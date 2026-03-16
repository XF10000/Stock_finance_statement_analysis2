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
from tushare_client import TushareClient
from market_data_manager import MarketDataManager


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


class MarketDataUpdater:
    """全A股数据更新器"""
    
    def __init__(self, config_path: str = 'config.yaml', 
                 db_path: str = 'database/market_data.db',
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
        self.db_manager = MarketDataManager(db_path)
        
        # 初始化限流器（200次/分钟）
        self.rate_limiter = RateLimiter(max_calls=200, period=60)
        
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
                        
                        try:
                            self.db_manager.save_financial_data(
                                ts_code=ts_code,
                                end_date=str(end_date),
                                data_type=table_name,
                                data=period_data
                            )
                            saved_count += 1
                        except Exception as e:
                            self.logger.warning(f"保存 {ts_code} {table_name} {end_date} 失败: {e}")
            
            if saved_count > 0:
                self.logger.info(f"✓ {ts_code} 成功保存 {saved_count} 条记录")
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
        
        # 使用线程池
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(self.fetch_stock_all_data, stock['ts_code'], force_update): stock
                for stock in stocks
            }
            
            # 处理完成的任务
            for i, future in enumerate(as_completed(futures), 1):
                stock = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"处理 {stock['ts_code']} 时发生异常: {e}")
                
                # 显示进度
                if i % 10 == 0 or i == len(stocks):
                    self._print_progress(i, len(stocks))
        
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
        db_stats = self.db_manager.get_database_stats()
        self.logger.info("\n数据库统计:")
        for table, count in db_stats.items():
            self.logger.info(f"  {table}: {count:,} 条记录")
        
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
                        try:
                            self.db_manager.save_financial_data(
                                ts_code=ts_code,
                                end_date=target_quarter,
                                data_type=table_name,
                                data=df_filtered
                            )
                            saved_count += 1
                        except Exception as e:
                            self.logger.warning(f"保存 {ts_code} {table_name} {target_quarter} 失败: {e}")
            
            if saved_count > 0:
                self.logger.info(f"✓ {ts_code} 成功保存 {saved_count} 条记录")
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
    
    def update_latest_quarter(self, target_quarter: str = None, 
                             calculate_indicators: bool = True):
        """
        增量更新最新季度的数据
        
        Args:
            target_quarter: 目标季度（如20241231），不指定则自动判断
            calculate_indicators: 是否自动计算核心指标
        """
        self.logger.info("="*60)
        self.logger.info("增量更新最新季度数据")
        self.logger.info("="*60)
        
        # 获取所有股票
        stocks = self.db_manager.get_all_stocks()
        
        if not stocks:
            self.logger.error("数据库中没有股票列表，请先运行 --init")
            return
        
        # 确定目标季度
        if not target_quarter:
            now = datetime.now()
            year = now.year
            month = now.month
            
            if month <= 4:
                target_quarter = f"{year-1}1231"
            elif month <= 8:
                target_quarter = f"{year}0331"
            elif month <= 10:
                target_quarter = f"{year}0630"
            else:
                target_quarter = f"{year}0930"
        
        self.logger.info(f"目标季度: {target_quarter}")
        self.logger.info(f"股票总数: {len(stocks)}")
        
        # 重置统计
        self.stats = {
            'total': len(stocks),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': time.time(),
            'failed_stocks': []
        }
        
        # 使用线程池更新
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.fetch_stock_incremental, stock['ts_code'], target_quarter): stock
                for stock in stocks
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                stock = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"处理 {stock['ts_code']} 时发生异常: {e}")
                
                if i % 10 == 0 or i == len(stocks):
                    self._print_progress(i, len(stocks))
        
        # 打印统计
        self._print_final_stats()
        
        # 计算核心指标
        if calculate_indicators and self.stats['success'] > 0:
            self.logger.info("\n" + "="*60)
            self.logger.info("开始计算核心指标...")
            self.logger.info("="*60)
            
            self.calculate_core_indicators_batch(target_quarter)
    
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
            balance_all = pd.read_sql_query(
                f"SELECT * FROM balancesheet WHERE ts_code IN ('{stock_codes_str}') AND end_date = '{target_quarter}'",
                conn
            )
            income_all = pd.read_sql_query(
                f"SELECT * FROM income WHERE ts_code IN ('{stock_codes_str}') AND end_date = '{target_quarter}'",
                conn
            )
            cashflow_all = pd.read_sql_query(
                f"SELECT * FROM cashflow WHERE ts_code IN ('{stock_codes_str}') AND end_date = '{target_quarter}'",
                conn
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
            balance_all = pd.read_sql_query(
                f"SELECT * FROM balancesheet WHERE ts_code IN ('{stock_codes_str}')",
                conn
            )
            income_all = pd.read_sql_query(
                f"SELECT * FROM income WHERE ts_code IN ('{stock_codes_str}')",
                conn
            )
            cashflow_all = pd.read_sql_query(
                f"SELECT * FROM cashflow WHERE ts_code IN ('{stock_codes_str}')",
                conn
            )
        
        self.logger.info(f"读取完成: 资产负债表 {len(balance_all)} 条, 利润表 {len(income_all)} 条, 现金流量表 {len(cashflow_all)} 条")
        
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
                    data_complete, update_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', insert_data)
            
            conn.commit()
            self.logger.info("批量写入完成")
        
        self.logger.info("\n" + "="*60)
        self.logger.info(f"核心指标计算完成: 成功 {success_count} 只，失败 {failed_count} 只")
        self.logger.info("="*60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='全A股数据更新程序')
    parser.add_argument('--init', action='store_true', 
                       help='首次初始化（获取全部历史数据）')
    parser.add_argument('--update-latest', action='store_true',
                       help='只更新最新季度数据（增量更新）')
    parser.add_argument('--quarter', type=str,
                       help='指定更新的季度（如20241231），不指定则自动判断')
    parser.add_argument('--no-indicators', action='store_true',
                       help='不自动计算核心指标')
    parser.add_argument('--recalculate-all', action='store_true',
                       help='强制重新计算所有股票的核心指标（忽略已有指标）')
    parser.add_argument('--force', action='store_true',
                       help='强制更新（忽略已有数据）')
    parser.add_argument('--resume', type=str,
                       help='从指定股票代码继续（断点续传）')
    parser.add_argument('--workers', type=int, default=5,
                       help='工作线程数（默认5）')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='配置文件路径')
    parser.add_argument('--db', type=str, default='database/market_data.db',
                       help='数据库路径')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('update_market_data.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # 初始化更新器
    updater = MarketDataUpdater(
        config_path=args.config,
        db_path=args.db,
        max_workers=args.workers
    )
    
    if args.init:
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
        
    elif args.update_latest:
        # 更新最新季度
        logger.info("="*60)
        logger.info("增量更新最新季度数据")
        logger.info("="*60)
        
        updater.update_latest_quarter(
            target_quarter=args.quarter,
            calculate_indicators=not args.no_indicators
        )
        
    elif args.recalculate_all:
        # 强制重新计算所有核心指标
        logger.info("="*60)
        logger.info("强制重新计算所有股票的核心指标")
        logger.info("="*60)
        
        # 清空现有指标
        conn = updater.db_manager.get_connection()
        cursor = conn.cursor()
        logger.info("清空现有核心指标数据...")
        cursor.execute('DELETE FROM core_indicators')
        conn.commit()
        logger.info("清空完成")
        
        # 重新计算所有指标
        updater.calculate_core_indicators_batch(
            target_quarter=args.quarter,
            updated_stocks=None  # None表示计算所有股票
        )
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
