"""
全A股数据更新程序
支持多线程并发获取、API限流、断点续传
"""

import argparse
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from datetime import datetime
import yaml
import os
from queue import Queue
import pandas as pd
from tqdm import tqdm
from tushare_client import TushareClient
from financial_data_manager import FinancialDataManager


class RateLimiter:
    """API限流器：控制请求频率"""
    
    def __init__(self, max_calls: int = 200, period: int = 60):
        """
        初始化限流器
        
        Args:
            max_calls: 时间窗口内最大调用次数
            period: 时间窗口（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = threading.Lock()
    
    def wait(self):
        """等待直到可以发起新请求"""
        with self.lock:
            now = time.time()
            
            # 移除过期的调用记录
            self.calls = [t for t in self.calls if now - t < self.period]
            
            # 如果达到限制，等待
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0]) + 0.1
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    # 清空记录重新开始
                    self.calls = []
            
            # 记录本次调用
            self.calls.append(time.time())


class FinancialDataUpdater:
    """全A股财务数据更新器"""
    
    def __init__(self, config_path: str = 'config.yaml', 
                 db_path: str = 'database/financial_data.db',
                 max_workers: int = 5):
        """
        初始化更新器
        
        Args:
            config_path: 配置文件路径
            db_path: 数据库路径
            max_workers: 最大工作线程数
        """
        self.config_path = config_path
        self.db_path = db_path
        self.max_workers = max_workers
        
        # 初始化日志
        self.logger = logging.getLogger(__name__)
        
        # 初始化数据库管理器
        self.db_manager = FinancialDataManager(db_path)
        
        # 初始化限流器（150次/分钟，留出安全余量避免触发 Tushare 限速）
        self.rate_limiter = RateLimiter(max_calls=150, period=60)
        
        # 统计信息
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'failed_stocks': []
        }
        self.stats_lock = threading.Lock()
        
        # 批量写入队列和线程
        self.write_queue = Queue()
        self.batch_size = 50  # 每批写入50条数据
        self.writer_running = False
        self.writer_thread = None
    
    def get_all_a_stocks(self, exclude_bse: bool = True) -> List[Dict]:
        """
        获取全A股列表（排除北交所）
        
        Args:
            exclude_bse: 是否排除北交所
            
        Returns:
            股票列表
        """
        self.logger.info("获取全A股列表...")
        
        # 初始化Tushare客户端
        client = TushareClient(config_path=self.config_path)
        
        # 获取股票列表
        df = client.pro.stock_basic(
            exchange='',
            list_status='L',  # 上市状态
            fields='ts_code,symbol,name,area,industry,market,list_date,delist_date'
        )
        
        if df is None or len(df) == 0:
            self.logger.error("获取股票列表失败")
            return []
        
        # 排除北交所
        if exclude_bse:
            df = df[~df['market'].isin(['北交所'])]
        
        # 检查是否ST股票
        df['is_st'] = df['name'].str.contains('ST', na=False).astype(int)
        
        stocks = df.to_dict('records')
        
        self.logger.info(f"获取到 {len(stocks)} 只股票")
        
        # 保存到数据库
        for stock in stocks:
            try:
                self.db_manager.add_stock(
                    ts_code=stock['ts_code'],
                    name=stock['name'],
                    market=stock.get('market', ''),
                    list_date=stock.get('list_date', ''),
                    delist_date=stock.get('delist_date'),
                    is_st=stock.get('is_st', 0)
                )
            except Exception as e:
                self.logger.warning(f"保存股票 {stock['ts_code']} 失败: {e}")
        
        return stocks
    
    def start_batch_writer(self):
        """启动批量写入线程"""
        if self.writer_running:
            return
        
        self.writer_running = True
        self.writer_thread = threading.Thread(
            target=self._batch_writer_worker,
            daemon=True,
            name="BatchWriter"
        )
        self.writer_thread.start()
        self.logger.info("批量写入线程已启动")
    
    def stop_batch_writer(self):
        """停止批量写入线程并等待队列清空"""
        if not self.writer_running:
            return
        
        self.logger.info("等待写入队列清空...")
        self.write_queue.put(None)  # 发送停止信号
        
        if self.writer_thread:
            self.writer_thread.join(timeout=60)  # 最多等待60秒
        
        self.writer_running = False
        self.logger.info("批量写入线程已停止")
    
    def _batch_writer_worker(self):
        """批量写入工作线程"""
        batch = []
        
        while self.writer_running:
            try:
                # 尝试获取数据，超时1秒
                item = self.write_queue.get(timeout=1)
                
                # 收到停止信号
                if item is None:
                    # 写入剩余数据
                    if batch:
                        self._write_batch(batch)
                    break
                
                batch.append(item)
                
                # 达到批量大小，立即写入
                if len(batch) >= self.batch_size:
                    self._write_batch(batch)
                    batch = []
                    
            except Exception as e:
                # 队列为空或超时，写入当前批次
                if batch:
                    self._write_batch(batch)
                    batch = []
    
    def _write_batch(self, batch: List[Dict]):
        """执行批量写入"""
        if not batch:
            return
        
        try:
            self.db_manager.save_financial_data_batch(batch)
            self.logger.debug(f"批量写入 {len(batch)} 条数据成功")
        except Exception as e:
            self.logger.error(f"批量写入失败: {e}")
            # 失败时尝试逐条写入
            for item in batch:
                try:
                    self.db_manager.save_financial_data(
                        ts_code=item['ts_code'],
                        end_date=item['end_date'],
                        data_type=item['data_type'],
                        data=item['data']
                    )
                except Exception as e2:
                    self.logger.error(f"单条写入失败 {item['ts_code']} {item['end_date']}: {e2}")
    
    
    def fetch_dividend_data(self, client: TushareClient, ts_code: str, max_retries: int = 2) -> Optional[pd.DataFrame]:
        """
        获取分红送股数据（带重试机制）
        根据该股票在数据库中的财务数据最新季度来确定获取范围
        
        Args:
            client: TushareClient实例
            ts_code: 股票代码
            max_retries: 最大重试次数
            
        Returns:
            分红送股数据DataFrame（中文列名）
        """
        import time
        import pandas as pd
        
        # 查询该股票在数据库中的最新财务数据季度
        end_date = None
        try:
            conn = self.db_manager.get_connection()
            query = f"""
                SELECT MAX(end_date) as latest_date
                FROM balancesheet
                WHERE ts_code = '{ts_code}'
            """
            result = pd.read_sql_query(query, conn)
            # 不关闭连接，让连接池管理
            
            if not result.empty and not pd.isna(result['latest_date'].iloc[0]):
                end_date = str(result['latest_date'].iloc[0])
                self.logger.debug(f"{ts_code} 财务数据最新季度: {end_date}，获取该季度及以前的分红数据")
        except Exception as e:
            self.logger.debug(f"查询 {ts_code} 最新财务季度失败: {e}，将获取所有分红数据")
        
        for attempt in range(max_retries + 1):
            try:
                # 等待限流
                self.rate_limiter.wait()
                
                # 获取所有分红数据
                df = client.pro.dividend(
                    ts_code=ts_code,
                    fields='end_date,ann_date,div_proc,stk_div,stk_bo_rate,stk_co_rate,cash_div,cash_div_tax,record_date,ex_date,pay_date,div_listdate,imp_ann_date'
                )
                
                if df is None or len(df) == 0:
                    self.logger.debug(f"{ts_code} 未获取到分红数据")
                    return None
                
                # 如果有财务数据的最新季度，则只保留该季度及以前的分红数据
                if end_date:
                    original_count = len(df)
                    df = df[df['end_date'] <= end_date]
                    filtered_count = len(df)
                    if filtered_count < original_count:
                        self.logger.debug(f"{ts_code} 根据财务数据最新季度 {end_date} 筛选分红: {original_count} → {filtered_count} 条")
                    
                    if len(df) == 0:
                        self.logger.debug(f"{ts_code} 筛选后无分红数据")
                        return None
                
                # 按报告期排序
                df = df.sort_values('end_date', ascending=False)
                
                # 重命名列为中文
                df_renamed = df.rename(columns={
                    'end_date': '报告期',
                    'ann_date': '公告日期',
                    'div_proc': '分红进度',
                    'stk_div': '送股比例',
                    'stk_bo_rate': '转增比例',
                    'stk_co_rate': '配股比例',
                    'cash_div': '每股派息(税前)',
                    'cash_div_tax': '每股派息(税后)',
                    'record_date': '股权登记日',
                    'ex_date': '除权除息日',
                    'pay_date': '派息日',
                    'div_listdate': '红股上市日',
                    'imp_ann_date': '实施公告日'
                })
                
                return df_renamed
                
            except Exception as e:
                error_msg = str(e)
                # 如果是 "No columns to parse" 错误且还有重试机会，则重试
                if "No columns to parse" in error_msg and attempt < max_retries:
                    self.logger.debug(f"{ts_code} API返回空响应，重试 {attempt + 1}/{max_retries}")
                    time.sleep(0.5)  # 等待 0.5 秒后重试
                    continue
                else:
                    # 最后一次尝试失败，或其他类型错误
                    if "No columns to parse" not in error_msg:
                        self.logger.warning(f"获取 {ts_code} 分红数据失败: {e}")
                    return None
        
        return None
    
    def fetch_stock_all_data(self, ts_code: str, force_update: bool = False) -> bool:
        """
        获取单只股票的全部历史财务数据
        参考 main.py 中的实现
        
        Args:
            ts_code: 股票代码
            force_update: 是否强制更新（忽略已有数据）
            
        Returns:
            是否成功
        """
        try:
            # 检查是否已有数据（如果不强制更新）
            if not force_update:
                # 检查是否已有最近的数据
                existing_data = self.db_manager.get_financial_data(
                    ts_code, 'balancesheet'
                )
                if len(existing_data) > 0:
                    self.logger.debug(f"{ts_code} 已有数据，跳过")
                    with self.stats_lock:
                        self.stats['skipped'] += 1
                    return True
            
            # 等待限流
            self.rate_limiter.wait()
            
            # 初始化Tushare客户端（每个线程独立）
            client = TushareClient(config_path=self.config_path)
            
            # 获取全部历史数据（不指定日期范围）
            self.logger.info(f"获取 {ts_code} 的全部历史数据...")
            data = client.get_all_financial_data(
                ts_code=ts_code,
                start_date=None,  # 不限制开始日期
                end_date=None,    # 不限制结束日期
                translate=True    # 翻译为中文字段名
            )
            
            if not data:
                self.logger.warning(f"{ts_code} 未获取到数据")
                with self.stats_lock:
                    self.stats['failed'] += 1
                    self.stats['failed_stocks'].append(ts_code)
                return False
            
            # 保存4张报表到数据库
            saved_count = 0
            for table_name in ['balancesheet', 'income', 'cashflow', 'fina_indicator']:
                if data.get(table_name) is not None and len(data[table_name]) > 0:
                    df = data[table_name]
                    
                    # 找到日期列（支持中英文）
                    date_col = None
                    for col in ['end_date', '报告期']:
                        if col in df.columns:
                            date_col = col
                            break
                    
                    if date_col is None:
                        self.logger.warning(f"{ts_code} {table_name} 缺少日期字段")
                        continue
                    
                    # 按报告期逐条保存
                    unique_dates = df[date_col].unique()
                    
                    for end_date in unique_dates:
                        # 筛选该报告期的数据
                        period_data = df[df[date_col] == end_date].copy()
                        
                        # 放入写入队列，而非直接写入
                        self.write_queue.put({
                            'ts_code': ts_code,
                            'end_date': str(end_date),
                            'data_type': table_name,
                            'data': period_data
                        })
                        saved_count += 1
            
            # 获取并保存分红数据
            try:
                dividend_df = self.fetch_dividend_data(client, ts_code)
                if dividend_df is not None and len(dividend_df) > 0:
                    self.db_manager.save_dividend_data(ts_code, dividend_df)
                    self.logger.info(f"✓ {ts_code} 成功保存 {len(dividend_df)} 条分红数据")
            except Exception as e:
                self.logger.warning(f"保存 {ts_code} 分红数据失败: {e}")
            
            if saved_count > 0:
                self.logger.info(f"✓ {ts_code} 成功保存 {saved_count} 条财务记录")
                with self.stats_lock:
                    self.stats['success'] += 1
                return True
            else:
                self.logger.warning(f"{ts_code} 未保存任何数据")
                with self.stats_lock:
                    self.stats['failed'] += 1
                    self.stats['failed_stocks'].append(ts_code)
                return False
                
        except Exception as e:
            self.logger.error(f"获取 {ts_code} 数据失败: {e}")
            with self.stats_lock:
                self.stats['failed'] += 1
                self.stats['failed_stocks'].append(ts_code)
            return False
    
    def update_all_stocks(self, stocks: List[Dict], force_update: bool = False,
                         resume_from: Optional[str] = None):
        """
        批量更新所有股票数据（多线程）
        
        Args:
            stocks: 股票列表
            force_update: 是否强制更新
            resume_from: 从指定股票代码继续（断点续传）
        """
        self.stats['total'] = len(stocks)
        self.stats['start_time'] = time.time()
        
        # 如果指定了断点续传
        if resume_from:
            resume_index = next((i for i, s in enumerate(stocks) if s['ts_code'] == resume_from), 0)
            stocks = stocks[resume_index:]
            self.logger.info(f"从 {resume_from} 继续，剩余 {len(stocks)} 只股票")
        
        self.logger.info(f"开始更新 {len(stocks)} 只股票的数据...")
        self.logger.info(f"使用 {self.max_workers} 个工作线程")
        
        # 启动批量写入线程
        self.start_batch_writer()
        
        try:
            # 使用线程池
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                futures = {
                    executor.submit(self.fetch_stock_all_data, stock['ts_code'], force_update): stock
                    for stock in stocks
                }
                
                # 使用 tqdm 进度条
                with tqdm(total=len(stocks), desc="数据采集进度", unit="只") as pbar:
                    for future in as_completed(futures):
                        stock = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            self.logger.error(f"处理 {stock['ts_code']} 时发生异常: {e}")
                        
                        # 更新进度条
                        pbar.update(1)
                        pbar.set_postfix({
                            '成功': self.stats['success'],
                            '失败': self.stats['failed'],
                            '跳过': self.stats['skipped']
                        })
        finally:
            # 停止批量写入线程并等待队列清空
            self.stop_batch_writer()
        
        # 打印最终统计
        self._print_final_stats()
    
    def _print_progress(self, current: int, total: int):
        """打印进度信息"""
        elapsed = time.time() - self.stats['start_time']
        speed = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0
        
        with self.stats_lock:
            self.logger.info(
                f"进度: {current}/{total} ({current/total*100:.1f}%) | "
                f"成功: {self.stats['success']} | "
                f"失败: {self.stats['failed']} | "
                f"跳过: {self.stats['skipped']} | "
                f"速度: {speed:.1f} 只/秒 | "
                f"预计剩余: {eta/60:.1f} 分钟"
            )
    
    def _print_final_stats(self):
        """打印最终统计信息"""
        elapsed = time.time() - self.stats['start_time']
        
        self.logger.info("\n" + "="*60)
        self.logger.info("数据更新完成")
        self.logger.info("="*60)
        self.logger.info(f"总计: {self.stats['total']} 只股票")
        self.logger.info(f"成功: {self.stats['success']} 只")
        self.logger.info(f"失败: {self.stats['failed']} 只")
        self.logger.info(f"跳过: {self.stats['skipped']} 只")
        self.logger.info(f"总耗时: {elapsed/60:.1f} 分钟")
        self.logger.info(f"平均速度: {self.stats['total']/elapsed:.2f} 只/秒")
        
        if self.stats['failed_stocks']:
            self.logger.warning(f"\n失败的股票 ({len(self.stats['failed_stocks'])} 只):")
            for ts_code in self.stats['failed_stocks'][:20]:  # 只显示前20个
                self.logger.warning(f"  - {ts_code}")
            if len(self.stats['failed_stocks']) > 20:
                self.logger.warning(f"  ... 还有 {len(self.stats['failed_stocks'])-20} 只")
        
        # 数据库统计
        try:
            db_stats = self.db_manager.get_database_stats()
            self.logger.info("\n数据库统计:")
            for table, count in db_stats.items():
                self.logger.info(f"  {table}: {count:,} 条记录")
        except Exception as e:
            self.logger.debug(f"获取数据库统计失败: {e}")
        
        self.logger.info("="*60 + "\n")
    
    def fetch_stock_incremental(self, ts_code: str, target_quarter: str = None) -> bool:
        """
        增量更新单只股票的最新季度数据
        
        Args:
            ts_code: 股票代码
            target_quarter: 目标季度（如20241231），不指定则自动判断
            
        Returns:
            是否成功
        """
        try:
            # 等待限流
            self.rate_limiter.wait()
            
            # 初始化Tushare客户端
            client = TushareClient(config_path=self.config_path)
            
            # 如果没有指定目标季度，自动判断最新季度
            if not target_quarter:
                now = datetime.now()
                year = now.year
                month = now.month
                
                # 判断当前应该是哪个季度
                if month <= 4:
                    # 1-4月，更新去年Q4数据
                    target_quarter = f"{year-1}1231"
                elif month <= 8:
                    # 5-8月，更新今年Q1数据
                    target_quarter = f"{year}0331"
                elif month <= 10:
                    # 9-10月，更新今年Q2数据
                    target_quarter = f"{year}0630"
                else:
                    # 11-12月，更新今年Q3数据
                    target_quarter = f"{year}0930"
            
            # 检查是否已有该季度数据
            if self.db_manager.check_data_exists(ts_code, target_quarter, 'balancesheet'):
                self.logger.debug(f"{ts_code} {target_quarter} 数据已存在，跳过")
                with self.stats_lock:
                    self.stats['skipped'] += 1
                return True
            
            # 获取该季度的数据（前后各扩展30天）
            start_date = str(int(target_quarter) - 100)  # 往前推一个月
            end_date = str(int(target_quarter) + 100)    # 往后推一个月
            
            self.logger.info(f"获取 {ts_code} 的 {target_quarter} 季度数据...")
            data = client.get_all_financial_data(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                translate=True
            )
            
            if not data:
                self.logger.warning(f"{ts_code} 未获取到数据")
                with self.stats_lock:
                    self.stats['failed'] += 1
                    self.stats['failed_stocks'].append(ts_code)
                return False
            
            # 保存数据
            saved_count = 0
            for table_name in ['balancesheet', 'income', 'cashflow', 'fina_indicator']:
                if data.get(table_name) is not None and len(data[table_name]) > 0:
                    df = data[table_name]
                    
                    # 找到日期列
                    date_col = None
                    for col in ['end_date', '报告期']:
                        if col in df.columns:
                            date_col = col
                            break
                    
                    if date_col is None:
                        continue
                    
                    # 只保存目标季度的数据
                    df_filtered = df[df[date_col] == target_quarter]
                    
                    if len(df_filtered) > 0:
                        # 放入写入队列，而非直接写入
                        self.write_queue.put({
                            'ts_code': ts_code,
                            'end_date': target_quarter,
                            'data_type': table_name,
                            'data': df_filtered
                        })
                        saved_count += 1
            
            # 注意：分红数据不在此处更新
            # 请使用 --update-dividend 参数专门更新分红数据
            # 总股本数据已从资产负债表中直接获取，不需要单独更新
            
            if saved_count > 0:
                self.logger.info(f"✓ {ts_code} 成功保存 {saved_count} 条财务记录")
                with self.stats_lock:
                    self.stats['success'] += 1
                return True
            else:
                with self.stats_lock:
                    self.stats['skipped'] += 1
                return True
                
        except Exception as e:
            self.logger.error(f"增量更新 {ts_code} 失败: {e}")
            with self.stats_lock:
                self.stats['failed'] += 1
                self.stats['failed_stocks'].append(ts_code)
            return False
    
    def _determine_target_quarter_smart(self) -> str:
        """
        智能判断目标季度（财务数据）
        根据当前月份判断应该尝试获取的季度：
        - 2-4月：尝试上年Q4
        - 5-7月：尝试本年Q1
        - 8-10月：尝试本年Q2
        - 11-1月：尝试本年Q3
        
        Returns:
            目标季度字符串，如 '20240930'
        """
        now = datetime.now()
        year = now.year
        month = now.month
        
        # 根据当前月份判断应该尝试获取的季度
        if 2 <= month <= 4:
            # 2-4月：尝试上年Q4
            target_quarter = f"{year-1}1231"
            self.logger.info(f"当前月份 {month}，尝试获取上年Q4: {target_quarter}")
        elif 5 <= month <= 7:
            # 5-7月：尝试本年Q1
            target_quarter = f"{year}0331"
            self.logger.info(f"当前月份 {month}，尝试获取本年Q1: {target_quarter}")
        elif 8 <= month <= 10:
            # 8-10月：尝试本年Q2
            target_quarter = f"{year}0630"
            self.logger.info(f"当前月份 {month}，尝试获取本年Q2: {target_quarter}")
        else:  # 11, 12, 1
            # 11-1月：尝试本年Q3
            target_quarter = f"{year}0930"
            self.logger.info(f"当前月份 {month}，尝试获取本年Q3: {target_quarter}")
        
        return target_quarter
    
    def _batch_check_missing_stocks(self, stocks: List[Dict], target_quarter: str) -> List[Dict]:
        """
        批量检查哪些股票缺少目标季度的数据
        使用单次 SQL 查询，避免逐只查询
        
        Args:
            stocks: 股票列表
            target_quarter: 目标季度
            
        Returns:
            需要更新的股票列表
        """
        import pandas as pd
        
        conn = self.db_manager.get_connection()
        
        try:
            # 提取所有股票代码
            stock_codes = [s['ts_code'] for s in stocks]
            
            # 构建 SQL IN 子句
            codes_str = "','".join(stock_codes)
            
            # 一次性查询所有已有数据的股票
            query = f"""
                SELECT DISTINCT ts_code 
                FROM balancesheet 
                WHERE ts_code IN ('{codes_str}') 
                AND end_date = '{target_quarter}'
            """
            
            existing_df = pd.read_sql_query(query, conn)
            existing_stocks = set(existing_df['ts_code'].tolist())
            
            # 找出缺失的股票
            stocks_need_update = [s for s in stocks if s['ts_code'] not in existing_stocks]
            
            self.logger.info(f"  已有数据: {len(existing_stocks)} 只")
            self.logger.info(f"  需要更新: {len(stocks_need_update)} 只")
            
            return stocks_need_update
            
        except Exception as e:
            self.logger.error(f"批量检查失败: {e}")
            # 出错时返回所有股票（保守策略）
            return stocks
        finally:
            conn.close()
    
    def update_latest_quarter(self, target_quarter: str = None, 
                             calculate_indicators: bool = True):
        """
        增量更新最新季度的数据
        优化：
        1. 智能季度判断：根据数据库中财务数据的最新时间确定目标季度
        2. 批量检查：先批量检查数据库，只对缺失的股票调用 API
        
        Args:
            target_quarter: 目标季度（如20241231），不指定则自动判断
            calculate_indicators: 是否自动计算核心指标
        """
        self.logger.info("="*60)
        self.logger.info("增量更新最新季度数据（优化版）")
        self.logger.info("="*60)
        
        # 获取所有股票
        stocks = self.db_manager.get_all_stocks()
        
        if not stocks:
            self.logger.error("数据库中没有股票列表，请先运行 --init")
            return
        
        # 优化1: 智能季度判断 - 如果未指定目标季度，根据数据库中的最新数据判断
        if not target_quarter:
            target_quarter = self._determine_target_quarter_smart()
            self.logger.info(f"智能判断目标季度: {target_quarter}")
        else:
            self.logger.info(f"指定目标季度: {target_quarter}")
        
        self.logger.info(f"股票总数: {len(stocks)}")
        
        # 优化2: 批量检查缺失数据
        self.logger.info("\n批量检查缺失数据...")
        stocks_need_update = self._batch_check_missing_stocks(stocks, target_quarter)
        
        if not stocks_need_update:
            self.logger.info("✓ 所有股票的数据都已是最新，无需更新")
            return
        
        self.logger.info(f"需要更新的股票: {len(stocks_need_update)} 只")
        self.logger.info(f"跳过的股票: {len(stocks) - len(stocks_need_update)} 只")
        
        # 重置统计
        self.stats = {
            'total': len(stocks_need_update),
            'success': 0,
            'failed': 0,
            'skipped': len(stocks) - len(stocks_need_update),
            'start_time': time.time(),
            'failed_stocks': []
        }
        
        # 启动批量写入线程
        self.start_batch_writer()
        
        try:
            # 使用线程池更新（只更新需要的股票）
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.fetch_stock_incremental, stock['ts_code'], target_quarter): stock
                    for stock in stocks_need_update
                }
                
                # 使用 tqdm 进度条
                with tqdm(total=len(stocks_need_update), desc=f"更新 {target_quarter}", unit="只") as pbar:
                    for future in as_completed(futures):
                        stock = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            self.logger.error(f"处理 {stock['ts_code']} 时发生异常: {e}")
                        
                        # 更新进度条
                        pbar.update(1)
                        pbar.set_postfix({
                            '成功': self.stats['success'],
                            '失败': self.stats['failed'],
                            '跳过': self.stats['skipped']
                        })
        finally:
            # 停止批量写入线程并等待队列清空
            self.stop_batch_writer()
        
        # 打印统计
        self._print_final_stats()
        
        # 计算核心指标
        if calculate_indicators and self.stats['success'] > 0:
            self.logger.info("\n" + "="*60)
            self.logger.info("开始计算核心指标...")
            self.logger.info("="*60)
            
            self.calculate_core_indicators_batch(target_quarter)
    
    def update_dividend_and_totalshares(self):
        """
        更新所有股票的分红数据（只更新缺失的）
        注：总股本数据已从资产负债表中直接获取，不需要单独更新
        使用单线程模式 + 批量写入，避免并发导致的 API 错误
        """
        self.logger.info("="*60)
        self.logger.info("更新分红数据（单线程模式）")
        self.logger.info("注：总股本数据已从资产负债表中直接获取，不需要单独更新")
        self.logger.info("="*60)
        
        # 获取所有股票
        stocks = self.db_manager.get_all_stocks()
        
        self.stats = {
            'total': len(stocks),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'dividend_updated': 0,
            'start_time': time.time(),
            'failed_stocks': []
        }
        
        # 初始化 Tushare 客户端（单线程模式只需要一个）
        client = TushareClient(config_path=self.config_path)
        
        # 批量存储待写入的分红数据
        dividend_batch = []
        batch_size = 50  # 每 50 条数据批量写入一次
        
        # 使用 tqdm 进度条，单线程顺序处理
        with tqdm(total=len(stocks), desc="更新分红数据", unit="只") as pbar:
            for stock in stocks:
                ts_code = stock['ts_code']
                
                try:
                    # 检查是否已有分红数据
                    existing_dividend = self.db_manager.get_dividend_data(ts_code)
                    
                    if existing_dividend is None or len(existing_dividend) == 0:
                        # 没有分红数据，获取
                        dividend_df = self.fetch_dividend_data(client, ts_code)
                        
                        if dividend_df is not None and len(dividend_df) > 0:
                            # 添加到批量写入列表
                            dividend_batch.append({
                                'ts_code': ts_code,
                                'data': dividend_df
                            })
                            
                            self.stats['dividend_updated'] += 1
                            self.stats['success'] += 1
                            
                            # 达到批量大小，执行写入
                            if len(dividend_batch) >= batch_size:
                                self._batch_save_dividend(dividend_batch)
                                dividend_batch = []
                        else:
                            self.stats['skipped'] += 1
                    else:
                        self.stats['skipped'] += 1
                        
                except Exception as e:
                    self.logger.error(f"更新 {ts_code} 分红数据失败: {e}")
                    self.stats['failed'] += 1
                    self.stats['failed_stocks'].append(ts_code)
                
                # 更新进度条
                pbar.update(1)
                pbar.set_postfix({
                    '成功': self.stats['success'],
                    '失败': self.stats['failed'],
                    '跳过': self.stats['skipped'],
                    '分红': self.stats['dividend_updated']
                })
        
        # 写入剩余的数据
        if dividend_batch:
            self._batch_save_dividend(dividend_batch)
        
        # 打印统计
        self._print_final_stats_dividend()
    
    def _batch_save_dividend(self, dividend_batch):
        """批量保存分红数据"""
        for item in dividend_batch:
            try:
                self.db_manager.save_dividend_data(item['ts_code'], item['data'])
            except Exception as e:
                self.logger.error(f"保存 {item['ts_code']} 分红数据失败: {e}")
    
    def _update_single_stock_dividend(self, ts_code: str) -> bool:
        """
        更新单只股票的分红数据（只更新缺失的）
        
        Args:
            ts_code: 股票代码
            
        Returns:
            是否成功
        """
        try:
            # 等待限流
            self.rate_limiter.wait()
            
            # 初始化Tushare客户端
            client = TushareClient(config_path=self.config_path)
            
            # 检查并更新分红数据
            existing_dividend = self.db_manager.get_dividend_data(ts_code)
            
            if existing_dividend is None or len(existing_dividend) == 0:
                # 没有分红数据，获取并保存
                self.logger.info(f"{ts_code}: 缺少分红数据")
                
                try:
                    dividend_df = self.fetch_dividend_data(client, ts_code)
                    if dividend_df is not None and len(dividend_df) > 0:
                        self.db_manager.save_dividend_data(ts_code, dividend_df)
                        self.logger.info(f"✓ {ts_code} 成功保存分红数据，共 {len(dividend_df)} 条")
                        with self.stats_lock:
                            self.stats['dividend_updated'] += 1
                            self.stats['success'] += 1
                        return True
                    else:
                        with self.stats_lock:
                            self.stats['skipped'] += 1
                        return True
                except Exception as e:
                    self.logger.warning(f"获取 {ts_code} 分红数据失败: {e}")
                    with self.stats_lock:
                        self.stats['failed'] += 1
                        self.stats['failed_stocks'].append(ts_code)
                    return False
            else:
                self.logger.debug(f"{ts_code}: 分红数据已存在，跳过")
                with self.stats_lock:
                    self.stats['skipped'] += 1
                return True
                
        except Exception as e:
            self.logger.error(f"更新 {ts_code} 分红数据失败: {e}")
            with self.stats_lock:
                self.stats['failed'] += 1
                self.stats['failed_stocks'].append(ts_code)
            return False
    
    def _print_final_stats_dividend(self):
        """打印分红更新最终统计"""
        print()  # 换行
        elapsed = time.time() - self.stats['start_time']
        
        self.logger.info("\n" + "="*60)
        self.logger.info("分红数据更新完成统计")
        self.logger.info("="*60)
        self.logger.info(f"总股票数: {self.stats['total']} 只")
        self.logger.info(f"成功: {self.stats['success']} 只")
        self.logger.info(f"失败: {self.stats['failed']} 只")
        self.logger.info(f"跳过: {self.stats['skipped']} 只")
        self.logger.info(f"分红数据更新: {self.stats['dividend_updated']} 只")
        self.logger.info(f"总耗时: {elapsed/60:.1f} 分钟")
        self.logger.info(f"平均速度: {self.stats['total']/elapsed:.2f} 只/秒")
        
        if self.stats['failed_stocks']:
            self.logger.warning(f"\n失败的股票 ({len(self.stats['failed_stocks'])} 只):")
            for ts_code in self.stats['failed_stocks'][:20]:
                self.logger.warning(f"  - {ts_code}")
            if len(self.stats['failed_stocks']) > 20:
                self.logger.warning(f"  ... 还有 {len(self.stats['failed_stocks'])-20} 只")
        
        self.logger.info("="*60 + "\n")
    
    def calculate_core_indicators_batch(self, target_quarter: str = None, 
                                       updated_stocks: List[str] = None):
        """
        批量计算核心指标（优化版：批量读取、内存计算、批量写入）
        
        Args:
            target_quarter: 目标季度，不指定则计算所有有数据的季度
            updated_stocks: 本次更新的股票列表，只计算这些股票的指标
        """
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        import sqlite3
        from tqdm import tqdm
        
        self.logger.info("使用优化算法批量计算核心指标...")
        
        conn = self.db_manager.get_connection()
        
        # 1. 确定需要计算的股票列表
        if updated_stocks:
            # 只计算本次更新的股票
            stocks_to_calc = updated_stocks
            self.logger.info(f"只计算本次更新的 {len(stocks_to_calc)} 只股票")
        else:
            # 计算所有股票
            stocks_df = pd.read_sql_query('SELECT DISTINCT ts_code FROM stock_list', conn)
            stocks_to_calc = stocks_df['ts_code'].tolist()
            self.logger.info(f"计算所有 {len(stocks_to_calc)} 只股票")
        
        if len(stocks_to_calc) == 0:
            self.logger.warning("没有需要计算的股票")
            return
        
        # 2. 批量读取财务数据
        self.logger.info("批量读取财务数据...")
        
        # 构建股票代码列表的SQL IN子句
        stock_codes_str = "','".join(stocks_to_calc)
        
        if target_quarter:
            # 只读取目标季度的数据
            self.logger.info(f"只读取 {target_quarter} 季度的数据")
            balance_all = self.db_manager.get_financial_data_batch_optimized(
                stocks_to_calc, 'balancesheet', target_quarter
            )
            income_all = self.db_manager.get_financial_data_batch_optimized(
                stocks_to_calc, 'income', target_quarter
            )
            cashflow_all = self.db_manager.get_financial_data_batch_optimized(
                stocks_to_calc, 'cashflow', target_quarter
            )
            
            # 检查哪些股票已有该季度的核心指标
            existing_indicators = pd.read_sql_query(
                f"SELECT DISTINCT ts_code FROM core_indicators WHERE ts_code IN ('{stock_codes_str}') AND end_date = '{target_quarter}'",
                conn
            )
            existing_stocks = set(existing_indicators['ts_code'].tolist())
            
            # 过滤掉已有指标的股票
            stocks_to_calc = [s for s in stocks_to_calc if s not in existing_stocks]
            
            if len(existing_stocks) > 0:
                self.logger.info(f"跳过已有指标的 {len(existing_stocks)} 只股票")
            
            if len(stocks_to_calc) == 0:
                self.logger.info("所有股票的指标都已存在，无需计算")
                return
        else:
            # 读取所有历史数据
            balance_all = self.db_manager.get_financial_data_batch_optimized(
                stocks_to_calc, 'balancesheet'
            )
            income_all = self.db_manager.get_financial_data_batch_optimized(
                stocks_to_calc, 'income'
            )
            cashflow_all = self.db_manager.get_financial_data_batch_optimized(
                stocks_to_calc, 'cashflow'
            )
        
        self.logger.info(f"读取完成: 资产负债表 {len(balance_all)} 条, 利润表 {len(income_all)} 条, 现金流量表 {len(cashflow_all)} 条")
        
        # 处理列名不一致问题（资产负债表和现金流量表用'TS股票代码'，利润表用'TS代码'）
        if len(balance_all) > 0 and 'TS股票代码' in balance_all.columns:
            balance_all = balance_all.rename(columns={'TS股票代码': 'ts_code'})
        if len(income_all) > 0 and 'TS代码' in income_all.columns:
            income_all = income_all.rename(columns={'TS代码': 'ts_code'})
        if len(cashflow_all) > 0 and 'TS股票代码' in cashflow_all.columns:
            cashflow_all = cashflow_all.rename(columns={'TS股票代码': 'ts_code'})
        
        # 3. 批量计算指标
        self.logger.info(f"开始计算 {len(stocks_to_calc)} 只股票的核心指标...")
        
        analyzer = CoreIndicatorsAnalyzer()
        all_indicators = []
        success_count = 0
        failed_count = 0
        
        for ts_code in tqdm(stocks_to_calc, desc="计算进度"):
            try:
                # 筛选当前股票的数据
                balance = balance_all[balance_all['ts_code'] == ts_code].copy()
                income = income_all[income_all['ts_code'] == ts_code].copy()
                cashflow = cashflow_all[cashflow_all['ts_code'] == ts_code].copy()
                
                if len(balance) == 0 or len(income) == 0 or len(cashflow) == 0:
                    failed_count += 1
                    continue
                
                # 计算指标
                indicators = analyzer.calculate_all_indicators(balance, income, cashflow)
                
                if len(indicators) > 0:
                    indicators['ts_code'] = ts_code
                    all_indicators.append(indicators)
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                self.logger.debug(f"计算 {ts_code} 核心指标失败: {e}")
        
        # 4. 批量写入数据库
        if len(all_indicators) > 0:
            self.logger.info(f"批量写入 {len(all_indicators)} 只股票的指标数据...")
            
            indicators_df = pd.concat(all_indicators, ignore_index=True)
            
            # 准备批量插入数据
            insert_data = []
            for _, row in indicators_df.iterrows():
                # 获取日期字段
                end_date = row.get('end_date') or row.get('报告期')
                if isinstance(end_date, str):
                    end_date = end_date.replace('-', '')
                
                insert_data.append((
                    row['ts_code'],
                    str(end_date),
                    row.get('ar_turnover_log') or row.get('应收账款周转率对数'),
                    row.get('gross_margin') or row.get('毛利率'),
                    row.get('lta_turnover_log') or row.get('长期经营资产周转率对数'),
                    row.get('working_capital_ratio') or row.get('净营运资本比率'),
                    row.get('ocf_ratio') or row.get('经营现金流比率'),
                    None,  # percentiles稍后计算
                    None,
                    None,
                    None,
                    None,
                    1,  # data_complete
                    0,  # is_ttm (年报指标，非TTM)
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            # 批量插入
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT OR REPLACE INTO core_indicators (
                    ts_code, end_date,
                    ar_turnover_log, gross_margin, lta_turnover_log,
                    working_capital_ratio, ocf_ratio,
                    ar_turnover_log_percentile, gross_margin_percentile,
                    lta_turnover_log_percentile, working_capital_ratio_percentile,
                    ocf_ratio_percentile,
                    data_complete, is_ttm, update_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', insert_data)
            
            conn.commit()
            self.logger.info("批量写入完成")
            
            # 自动更新分位数
            self.logger.info("\n自动更新分位数排名...")
            try:
                from financial_data_analyzer import FinancialDataAnalyzer
                analyzer_market = FinancialDataAnalyzer(self.db_manager)
                
                # 获取需要更新的季度
                quarters = set()
                for _, row in indicators_df.iterrows():
                    end_date = row.get('end_date') or row.get('报告期')
                    if isinstance(end_date, str):
                        end_date = end_date.replace('-', '')
                    quarters.add(str(int(end_date)))
                
                total_updated = 0
                for quarter in quarters:
                    count = analyzer_market.update_percentile_ranks(quarter)
                    total_updated += count
                
                self.logger.info(f"✓ 已更新 {len(quarters)} 个季度的分位数，共 {total_updated} 条记录")
            except Exception as e:
                self.logger.warning(f"⚠️  更新分位数失败: {e}")
        
        self.logger.info("\n" + "="*60)
        self.logger.info(f"核心指标计算完成: 成功 {success_count} 只，失败 {failed_count} 只")
        self.logger.info("="*60)
    
    def calculate_ttm_indicators_batch(self, updated_stocks: List[str] = None):
        """
        批量计算 TTM 核心指标
        为每个季度（Q1/Q2/Q3/Q4）生成 TTM 指标并存储到数据库
        
        Args:
            updated_stocks: 本次更新的股票列表，只计算这些股票的指标
        """
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        from ttm_generator import TTMGenerator
        from tqdm import tqdm
        
        self.logger.info("="*60)
        self.logger.info("批量计算 TTM 核心指标...")
        self.logger.info("="*60)
        
        conn = self.db_manager.get_connection()
        
        # 1. 确定需要计算的股票列表
        if updated_stocks:
            stocks_to_calc = updated_stocks
            self.logger.info(f"只计算本次更新的 {len(stocks_to_calc)} 只股票")
        else:
            stocks_df = pd.read_sql_query('SELECT DISTINCT ts_code FROM stock_list', conn)
            stocks_to_calc = stocks_df['ts_code'].tolist()
            self.logger.info(f"计算所有 {len(stocks_to_calc)} 只股票")
        
        if len(stocks_to_calc) == 0:
            self.logger.warning("没有需要计算的股票")
            return
        
        # 2. 批量读取财务数据
        self.logger.info("批量读取财务数据...")
        balance_all = self.db_manager.get_financial_data_batch_optimized(
            stocks_to_calc, 'balancesheet'
        )
        income_all = self.db_manager.get_financial_data_batch_optimized(
            stocks_to_calc, 'income'
        )
        cashflow_all = self.db_manager.get_financial_data_batch_optimized(
            stocks_to_calc, 'cashflow'
        )
        
        # 列名统一化
        if len(balance_all) > 0 and 'TS股票代码' in balance_all.columns:
            balance_all = balance_all.rename(columns={'TS股票代码': 'ts_code'})
        if len(income_all) > 0 and 'TS代码' in income_all.columns:
            income_all = income_all.rename(columns={'TS代码': 'ts_code'})
        if len(cashflow_all) > 0 and 'TS股票代码' in cashflow_all.columns:
            cashflow_all = cashflow_all.rename(columns={'TS股票代码': 'ts_code'})
        
        self.logger.info(f"读取完成: 资产负债表 {len(balance_all)} 条, 利润表 {len(income_all)} 条, 现金流量表 {len(cashflow_all)} 条")
        
        # 3. 批量计算 TTM 指标
        self.logger.info(f"开始计算 {len(stocks_to_calc)} 只股票的 TTM 核心指标...")
        
        generator = TTMGenerator()
        analyzer = CoreIndicatorsAnalyzer()
        all_indicators = []
        success_count = 0
        failed_count = 0
        
        for ts_code in tqdm(stocks_to_calc, desc="TTM 计算进度"):
            try:
                # 筛选当前股票的数据
                balance = balance_all[balance_all['ts_code'] == ts_code].copy()
                income = income_all[income_all['ts_code'] == ts_code].copy()
                cashflow = cashflow_all[cashflow_all['ts_code'] == ts_code].copy()
                
                if len(balance) == 0 or len(income) == 0 or len(cashflow) == 0:
                    failed_count += 1
                    continue
                
                # 获取所有季度
                date_col = '报告期' if '报告期' in balance.columns else 'end_date'
                all_quarters = sorted([str(q).replace('-', '') for q in balance[date_col].unique()])
                
                # 为每个季度生成 TTM 指标（跳过年报季度）
                for quarter in all_quarters:
                    try:
                        # 年报季度（1231）不需要计算 TTM，因为年报本身就是完整年度数据
                        if quarter.endswith('1231'):
                            continue
                        
                        # 生成 TTM 财务数据
                        ttm_data = generator.generate_ttm_data(
                            balance, income, cashflow, quarter
                        )
                        
                        if not ttm_data:
                            continue
                        
                        # 计算 TTM 核心指标（数据已经是 TTM 格式）
                        indicators = analyzer.calculate_all_indicators(
                            ttm_data['balance'],
                            ttm_data['income'],
                            ttm_data['cashflow'],
                            is_ttm_data=True
                        )
                        
                        if len(indicators) > 0:
                            indicators['ts_code'] = ts_code
                            indicators['end_date'] = quarter
                            indicators['is_ttm'] = 1
                            all_indicators.append(indicators)
                    
                    except Exception as e:
                        self.logger.debug(f"计算 {ts_code} {quarter} TTM 指标失败: {e}")
                        continue
                
                if len([ind for ind in all_indicators if ind['ts_code'].iloc[0] == ts_code]) > 0:
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                self.logger.debug(f"处理 {ts_code} 失败: {e}")
        
        # 4. 批量写入数据库
        if len(all_indicators) > 0:
            self.logger.info(f"批量写入 {len(all_indicators)} 条 TTM 指标数据...")
            
            indicators_df = pd.concat(all_indicators, ignore_index=True)
            
            # 准备批量插入数据
            insert_data = []
            for _, row in indicators_df.iterrows():
                end_date = row.get('end_date')
                if isinstance(end_date, str):
                    end_date = end_date.replace('-', '')
                
                insert_data.append((
                    row['ts_code'],
                    str(end_date),
                    row.get('ar_turnover_log') or row.get('应收账款周转率对数'),
                    row.get('gross_margin') or row.get('毛利率'),
                    row.get('lta_turnover_log') or row.get('长期经营资产周转率对数'),
                    row.get('working_capital_ratio') or row.get('净营运资本比率'),
                    row.get('ocf_ratio') or row.get('经营现金流比率'),
                    None,  # percentiles稍后计算
                    None,
                    None,
                    None,
                    None,
                    1,  # data_complete
                    1,  # is_ttm
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            # 批量插入
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT OR REPLACE INTO core_indicators (
                    ts_code, end_date,
                    ar_turnover_log, gross_margin, lta_turnover_log,
                    working_capital_ratio, ocf_ratio,
                    ar_turnover_log_percentile, gross_margin_percentile,
                    lta_turnover_log_percentile, working_capital_ratio_percentile,
                    ocf_ratio_percentile,
                    data_complete, is_ttm, update_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', insert_data)
            
            conn.commit()
            self.logger.info("批量写入完成")
            
            # 自动更新分位数
            self.logger.info("\n自动更新 TTM 分位数排名...")
            try:
                from financial_data_analyzer import FinancialDataAnalyzer
                analyzer_market = FinancialDataAnalyzer(self.db_manager)
                
                # 获取需要更新的季度
                quarters = set()
                for _, row in indicators_df.iterrows():
                    end_date = row.get('end_date')
                    if isinstance(end_date, str):
                        end_date = end_date.replace('-', '')
                    quarters.add(str(int(end_date)))
                
                total_updated = 0
                for quarter in quarters:
                    # 更新 TTM 分位数（is_ttm=1）
                    count = analyzer_market.update_percentile_ranks(quarter, is_ttm=True)
                    total_updated += count
                
                self.logger.info(f"✓ 已更新 {len(quarters)} 个季度的 TTM 分位数，共 {total_updated} 条记录")
            except Exception as e:
                self.logger.warning(f"⚠️  更新 TTM 分位数失败: {e}")
        
        self.logger.info("\n" + "="*60)
        self.logger.info(f"TTM 核心指标计算完成: 成功 {success_count} 只，失败 {failed_count} 只")
        self.logger.info("="*60)


def normalize_stock_code(ts_code: str) -> str:
    """
    规范化股票代码，自动补全交易所后缀
    
    Args:
        ts_code: 股票代码（可以带或不带后缀）
        
    Returns:
        规范化后的股票代码（带交易所后缀）
    
    Examples:
        '000333' -> '000333.SZ'
        '600519' -> '600519.SH'
        '000001.SZ' -> '000001.SZ'
    """
    # 如果已经有后缀，直接返回
    if '.' in ts_code:
        return ts_code.upper()
    
    # 去除可能的空格
    code = ts_code.strip()
    
    # 深圳：000、002、003、300开头
    # 上海：600、601、603、605、688开头
    if code.startswith(('000', '002', '003', '300')):
        return f"{code}.SZ"
    elif code.startswith(('600', '601', '603', '605', '688')):
        return f"{code}.SH"
    else:
        # 默认深圳（兼容其他代码）
        return f"{code}.SZ"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='全A股财务数据更新程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 首次初始化（获取所有A股的全部历史数据）
  python update_financial_data.py --init
  
  # 增量更新最新季度的财务四表数据和核心指标
  python update_financial_data.py --update-latest
  
  # 更新单只股票的最新季度数据
  python update_financial_data.py --update-stock 000001
  
  # 更新单只股票的完整历史数据
  python update_financial_data.py --update-stock 000001 --full
  
  # 更新单只股票的分红数据
  python update_financial_data.py --update-stock-dividend 000001
  
  # 更新所有股票的分红数据（补充缺失数据）
  python update_financial_data.py --update-dividend
  
  # 指定季度更新
  python update_financial_data.py --update-latest --quarter 20241231
  
  # 强制重新计算所有核心指标
  python update_financial_data.py --recalculate-all
  
  # 断点续传（从指定股票继续）
  python update_financial_data.py --init --resume 000333
        """
    )
    
    # 主要操作参数
    parser.add_argument('--init', action='store_true',
                       help='首次初始化：获取所有A股的全部历史数据（财务四表+分红，总股本从资产负债表获取）')
    parser.add_argument('--update-latest', action='store_true',
                       help='增量更新：只更新最新季度的财务四表数据和核心指标（不包括分红）')
    parser.add_argument('--update-stock', type=str, metavar='CODE',
                       help='更新单只股票（例如：000001 或 600519.SH），默认增量更新最新季度，配合 --full 可更新全部历史数据')
    parser.add_argument('--update-stock-dividend', type=str, metavar='CODE',
                       help='更新单只股票的分红数据（例如：000001 或 600519.SH）')
    parser.add_argument('--update-dividend', action='store_true',
                       help='更新所有股票的分红数据（补充缺失数据，不重复获取已有数据）')
    parser.add_argument('--recalculate-all', action='store_true',
                       help='强制重新计算所有股票的核心指标（清空现有指标后重新计算）')
    parser.add_argument('--full', action='store_true',
                       help='完整更新：获取全部历史数据（仅在 --update-stock 时有效）')
    
    # 辅助参数
    parser.add_argument('--quarter', type=str,
                       help='指定更新的季度（格式：YYYYMMDD，如 20241231），不指定则自动判断当前应更新的季度')
    parser.add_argument('--no-indicators', action='store_true',
                       help='不自动计算核心指标（仅在 --update-latest 时有效）')
    parser.add_argument('--force', action='store_true',
                       help='强制更新：忽略已有数据，重新获取（慎用，会消耗大量API积分）')
    parser.add_argument('--resume', type=str, metavar='CODE',
                       help='断点续传：从指定股票代码继续（例如：000333 或 000333.SZ）')
    
    # 配置参数
    parser.add_argument('--workers', type=int, default=5,
                       help='并发线程数（默认：5，建议范围：2-8）')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='配置文件路径（默认：config.yaml）')
    parser.add_argument('--db', type=str, default='database/financial_data.db',
                       help='数据库文件路径（默认：database/financial_data.db）')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别（默认：INFO）')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('update_financial_data.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # 规范化 resume 参数（如果有）
    if args.resume:
        args.resume = normalize_stock_code(args.resume)
        logger.info(f"断点续传股票代码规范化为: {args.resume}")
    
    # 规范化 update_stock 参数（如果有）
    if args.update_stock:
        args.update_stock = normalize_stock_code(args.update_stock)
        logger.info(f"更新股票代码规范化为: {args.update_stock}")
    
    # 规范化 update_stock_dividend 参数（如果有）
    if args.update_stock_dividend:
        args.update_stock_dividend = normalize_stock_code(args.update_stock_dividend)
        logger.info(f"更新分红股票代码规范化为: {args.update_stock_dividend}")
    
    # 初始化更新器
    updater = FinancialDataUpdater(
        config_path=args.config,
        db_path=args.db,
        max_workers=args.workers
    )
    
    if args.update_stock_dividend:
        # 更新单只股票的分红数据
        logger.info("="*60)
        logger.info(f"更新单只股票的分红数据: {args.update_stock_dividend}")
        logger.info("="*60)
        
        try:
            # 初始化Tushare客户端
            client = TushareClient(config_path=args.config)
            
            # 获取分红数据
            logger.info(f"正在获取 {args.update_stock_dividend} 的分红数据...")
            dividend_df = updater.fetch_dividend_data(client, args.update_stock_dividend)
            
            if dividend_df is not None and len(dividend_df) > 0:
                # 保存到数据库
                updater.db_manager.save_dividend_data(args.update_stock_dividend, dividend_df)
                logger.info(f"✓ {args.update_stock_dividend} 分红数据更新成功，共 {len(dividend_df)} 条记录")
            else:
                logger.warning(f"⚠️  {args.update_stock_dividend} 未获取到分红数据")
                
        except Exception as e:
            logger.error(f"✗ {args.update_stock_dividend} 分红数据更新失败: {e}")
            import traceback
            traceback.print_exc()
    
    elif args.update_stock:
        # 更新单只股票
        logger.info("="*60)
        if args.full:
            logger.info(f"更新单只股票的完整历史数据: {args.update_stock}")
        else:
            logger.info(f"更新单只股票的最新季度数据: {args.update_stock}")
        logger.info("="*60)
        
        if args.full:
            # 完整更新
            success = updater.fetch_stock_all_data(args.update_stock, force_update=True)
            if success:
                logger.info(f"\n✓ {args.update_stock} 完整历史数据更新成功")
            else:
                logger.error(f"\n✗ {args.update_stock} 完整历史数据更新失败")
        else:
            # 增量更新最新季度
            target_quarter = args.quarter if args.quarter else updater._determine_target_quarter_smart()
            logger.info(f"目标季度: {target_quarter}")
            
            success = updater.fetch_stock_incremental(args.update_stock, target_quarter)
            if success:
                logger.info(f"\n✓ {args.update_stock} 最新季度数据更新成功")
                
                # 计算核心指标
                if not args.no_indicators:
                    logger.info("\n计算核心指标...")
                    try:
                        updater.calculate_core_indicators_batch(
                            updated_stocks=[args.update_stock]
                        )
                        logger.info("✓ 核心指标计算完成")
                    except Exception as e:
                        logger.error(f"计算核心指标失败: {e}")
            else:
                logger.error(f"\n✗ {args.update_stock} 最新季度数据更新失败")
        
    elif args.init:
        # 首次初始化
        logger.info("="*60)
        logger.info("首次初始化：获取全A股数据")
        logger.info("="*60)
        
        # 获取股票列表
        stocks = updater.get_all_a_stocks(exclude_bse=True)
        
        if not stocks:
            logger.error("获取股票列表失败")
            return
        
        # 更新所有股票数据
        updater.update_all_stocks(
            stocks=stocks,
            force_update=args.force,
            resume_from=args.resume
        )
        
        # 自动计算核心指标（年报 + TTM）
        logger.info("\n" + "="*60)
        logger.info("开始计算核心指标（年报 + TTM）...")
        logger.info("="*60)
        
        try:
            # 计算年报核心指标
            updater.calculate_core_indicators_batch()
            
            # 计算 TTM 核心指标
            updater.calculate_ttm_indicators_batch()
            
            logger.info("\n✓ 核心指标计算完成")
        except Exception as e:
            logger.error(f"计算核心指标失败: {e}")
            import traceback
            traceback.print_exc()
        
    elif args.update_latest:
        # 更新最新季度
        logger.info("="*60)
        logger.info("增量更新最新季度数据")
        logger.info("="*60)
        
        updater.update_latest_quarter(
            target_quarter=args.quarter,
            calculate_indicators=not args.no_indicators
        )
        
    elif args.update_dividend:
        # 更新分红数据
        logger.info("="*60)
        logger.info("更新所有股票的分红数据")
        logger.info("注：总股本数据已从资产负债表中直接获取，不需要单独更新")
        logger.info("="*60)
        
        updater.update_dividend_and_totalshares()
        
    elif args.recalculate_all:
        # 强制重新计算所有核心指标（年报 + TTM）
        logger.info("="*60)
        logger.info("强制重新计算所有股票的核心指标（年报 + TTM）")
        logger.info("="*60)
        
        # 清空现有指标
        conn = updater.db_manager.get_connection()
        cursor = conn.cursor()
        logger.info("清空现有核心指标数据...")
        cursor.execute('DELETE FROM core_indicators')
        conn.commit()
        logger.info("清空完成\n")
        
        # 一次性读取所有数据，分别计算年报和 TTM 指标
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        from ttm_generator import TTMGenerator
        from tqdm import tqdm
        
        # 1. 获取股票列表
        stocks_df = pd.read_sql_query('SELECT DISTINCT ts_code FROM stock_list', conn)
        stocks_to_calc = stocks_df['ts_code'].tolist()
        logger.info(f"计算所有 {len(stocks_to_calc)} 只股票\n")
        
        # 2. 批量读取财务数据（只读取一次）
        logger.info("批量读取财务数据...")
        balance_all = updater.db_manager.get_financial_data_batch_optimized(
            stocks_to_calc, 'balancesheet'
        )
        income_all = updater.db_manager.get_financial_data_batch_optimized(
            stocks_to_calc, 'income'
        )
        cashflow_all = updater.db_manager.get_financial_data_batch_optimized(
            stocks_to_calc, 'cashflow'
        )
        
        # 列名统一化
        if len(balance_all) > 0 and 'TS股票代码' in balance_all.columns:
            balance_all = balance_all.rename(columns={'TS股票代码': 'ts_code'})
        if len(income_all) > 0 and 'TS代码' in income_all.columns:
            income_all = income_all.rename(columns={'TS代码': 'ts_code'})
        if len(cashflow_all) > 0 and 'TS股票代码' in cashflow_all.columns:
            cashflow_all = cashflow_all.rename(columns={'TS股票代码': 'ts_code'})
        
        logger.info(f"数据读取完成\n")
        
        # 3. 计算年报和 TTM 指标
        logger.info("开始计算核心指标（年报 + TTM）...")
        
        analyzer = CoreIndicatorsAnalyzer()
        generator = TTMGenerator()
        all_annual_indicators = []
        all_ttm_indicators = []
        success_count = 0
        failed_count = 0
        
        for ts_code in tqdm(stocks_to_calc, desc="计算进度"):
            try:
                # 筛选当前股票的数据
                balance = balance_all[balance_all['ts_code'] == ts_code].copy()
                income = income_all[income_all['ts_code'] == ts_code].copy()
                cashflow = cashflow_all[cashflow_all['ts_code'] == ts_code].copy()
                
                if len(balance) == 0 or len(income) == 0 or len(cashflow) == 0:
                    failed_count += 1
                    continue
                
                # 计算年报指标
                annual_indicators = analyzer.calculate_all_indicators(balance, income, cashflow)
                if len(annual_indicators) > 0:
                    annual_indicators['ts_code'] = ts_code
                    annual_indicators['is_ttm'] = 0
                    all_annual_indicators.append(annual_indicators)
                
                # 计算 TTM 指标
                date_col = '报告期' if '报告期' in balance.columns else 'end_date'
                all_quarters = sorted([str(q).replace('-', '') for q in balance[date_col].unique()])
                
                ttm_count = 0
                for quarter in all_quarters:
                    try:
                        ttm_data = generator.generate_ttm_data(balance, income, cashflow, quarter)
                        if not ttm_data:
                            continue
                        
                        ttm_indicators = analyzer.calculate_all_indicators(
                            ttm_data['balance'],
                            ttm_data['income'],
                            ttm_data['cashflow'],
                            is_ttm_data=True
                        )
                        
                        if len(ttm_indicators) > 0:
                            ttm_indicators['ts_code'] = ts_code
                            ttm_indicators['end_date'] = quarter
                            ttm_indicators['is_ttm'] = 1
                            all_ttm_indicators.append(ttm_indicators)
                            ttm_count += 1
                    except Exception as e:
                        logger.warning(f"计算 {ts_code} {quarter} TTM 指标失败: {e}")
                        continue
                
                if ttm_count > 0:
                    logger.debug(f"{ts_code}: 成功计算 {ttm_count} 个季度的 TTM 指标")
                
                success_count += 1
                    
            except Exception as e:
                failed_count += 1
                logger.debug(f"处理 {ts_code} 失败: {e}")
        
        # 4. 批量写入年报指标
        if len(all_annual_indicators) > 0:
            logger.info(f"\n批量写入年报指标数据...")
            indicators_df = pd.concat(all_annual_indicators, ignore_index=True)
            
            # 只保留年报季度（12月31日）的记录
            date_col = 'end_date' if 'end_date' in indicators_df.columns else '报告期'
            indicators_df['_end_date_str'] = indicators_df[date_col].astype(str).str.replace('-', '')
            indicators_df = indicators_df[indicators_df['_end_date_str'].str.endswith('1231')]
            logger.info(f"  过滤后保留 {len(indicators_df)} 条年报记录")
            
            insert_data = []
            for _, row in indicators_df.iterrows():
                end_date = row.get('end_date') or row.get('报告期')
                if isinstance(end_date, str):
                    end_date = end_date.replace('-', '')
                
                insert_data.append((
                    row['ts_code'],
                    str(end_date),
                    row.get('ar_turnover_log') or row.get('应收账款周转率对数'),
                    row.get('gross_margin') or row.get('毛利率'),
                    row.get('lta_turnover_log') or row.get('长期经营资产周转率对数'),
                    row.get('working_capital_ratio') or row.get('净营运资本比率'),
                    row.get('ocf_ratio') or row.get('经营现金流比率'),
                    None, None, None, None, None,
                    1,  # data_complete
                    0,  # is_ttm
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            cursor.executemany('''
                INSERT OR REPLACE INTO core_indicators (
                    ts_code, end_date,
                    ar_turnover_log, gross_margin, lta_turnover_log,
                    working_capital_ratio, ocf_ratio,
                    ar_turnover_log_percentile, gross_margin_percentile,
                    lta_turnover_log_percentile, working_capital_ratio_percentile,
                    ocf_ratio_percentile,
                    data_complete, is_ttm, update_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', insert_data)
            conn.commit()
            logger.info(f"✓ 年报指标写入完成")
        
        # 5. 批量写入 TTM 指标
        logger.info(f"\n收集到 {len(all_ttm_indicators)} 只股票的 TTM 指标")
        if len(all_ttm_indicators) > 0:
            logger.info(f"批量写入 TTM 指标数据...")
            indicators_df = pd.concat(all_ttm_indicators, ignore_index=True)
            logger.info(f"  合并后共 {len(indicators_df)} 条 TTM 记录")
            
            insert_data = []
            for _, row in indicators_df.iterrows():
                end_date = row.get('end_date')
                if isinstance(end_date, str):
                    end_date = end_date.replace('-', '')
                
                insert_data.append((
                    row['ts_code'],
                    str(end_date),
                    row.get('ar_turnover_log') or row.get('应收账款周转率对数'),
                    row.get('gross_margin') or row.get('毛利率'),
                    row.get('lta_turnover_log') or row.get('长期经营资产周转率对数'),
                    row.get('working_capital_ratio') or row.get('净营运资本比率'),
                    row.get('ocf_ratio') or row.get('经营现金流比率'),
                    None, None, None, None, None,
                    1,  # data_complete
                    1,  # is_ttm
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            cursor.executemany('''
                INSERT OR REPLACE INTO core_indicators (
                    ts_code, end_date,
                    ar_turnover_log, gross_margin, lta_turnover_log,
                    working_capital_ratio, ocf_ratio,
                    ar_turnover_log_percentile, gross_margin_percentile,
                    lta_turnover_log_percentile, working_capital_ratio_percentile,
                    ocf_ratio_percentile,
                    data_complete, is_ttm, update_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', insert_data)
            conn.commit()
            logger.info(f"✓ TTM 指标写入完成")
        
        # 6. 更新分位数
        logger.info("\n更新分位数排名...")
        try:
            from financial_data_analyzer import FinancialDataAnalyzer
            analyzer_market = FinancialDataAnalyzer(updater.db_manager)
            
            # 获取所有季度
            all_quarters = set()
            if len(all_annual_indicators) > 0:
                for _, row in pd.concat(all_annual_indicators, ignore_index=True).iterrows():
                    end_date = row.get('end_date') or row.get('报告期')
                    if isinstance(end_date, str):
                        end_date = end_date.replace('-', '')
                    all_quarters.add(str(int(end_date)))
            
            if len(all_ttm_indicators) > 0:
                for _, row in pd.concat(all_ttm_indicators, ignore_index=True).iterrows():
                    end_date = row.get('end_date')
                    if isinstance(end_date, str):
                        end_date = end_date.replace('-', '')
                    all_quarters.add(str(int(end_date)))
            
            # 更新年报分位数
            total_updated = 0
            for quarter in all_quarters:
                count = analyzer_market.update_percentile_ranks(quarter, is_ttm=False)
                total_updated += count
            
            # 更新 TTM 分位数
            for quarter in all_quarters:
                count = analyzer_market.update_percentile_ranks(quarter, is_ttm=True)
                total_updated += count
            
            logger.info(f"✓ 已更新 {len(all_quarters)} 个季度的分位数，共 {total_updated} 条记录")
        except Exception as e:
            logger.warning(f"⚠️  更新分位数失败: {e}")
        
        logger.info("\n" + "="*60)
        logger.info(f"所有核心指标计算完成: 成功 {success_count} 只，失败 {failed_count} 只")
        logger.info(f"  年报指标: {len(all_annual_indicators)} 条")
        logger.info(f"  TTM 指标: {len(all_ttm_indicators)} 条")
        logger.info("="*60)
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
