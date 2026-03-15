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
    
    def update_latest_quarter(self):
        """只更新最新季度的数据"""
        self.logger.info("更新最新季度数据...")
        
        # 获取所有股票
        stocks = self.db_manager.get_all_stocks()
        
        if not stocks:
            self.logger.error("数据库中没有股票列表，请先运行 --init")
            return
        
        # TODO: 实现增量更新逻辑
        # 1. 确定最新季度
        # 2. 只更新该季度的数据
        
        self.logger.warning("增量更新功能待实现")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='全A股数据更新程序')
    parser.add_argument('--init', action='store_true', 
                       help='首次初始化（获取全部历史数据）')
    parser.add_argument('--update-latest', action='store_true',
                       help='只更新最新季度数据')
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
        logger.info("更新最新季度数据")
        logger.info("="*60)
        
        updater.update_latest_quarter()
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
