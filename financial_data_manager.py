"""
财务数据管理器
使用SQLite数据库管理全A股财务数据，支持多线程安全访问
"""

import sqlite3
import threading
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging
import os
from io import StringIO


class FinancialDataManager:
    """财务数据管理器 - 管理全A股财务数据的SQLite数据库"""
    
    def __init__(self, db_path: str = 'database/financial_data.db'):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # 确保数据库目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            self.logger.info(f"创建数据库目录: {db_dir}")
        
        # 使用线程本地存储，每个线程独立连接
        self.local = threading.local()
        
        # 初始化数据库
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        获取线程本地的数据库连接
        每个线程使用独立连接，避免多线程冲突
        
        Returns:
            数据库连接对象
        """
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            self.local.conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,  # 30秒超时
                isolation_level='DEFERRED',  # 延迟锁定
                check_same_thread=False  # 允许跨线程使用（配合线程本地存储）
            )
            # 启用WAL模式，支持并发读写
            self.local.conn.execute('PRAGMA journal_mode=WAL')
            # 启用外键约束
            self.local.conn.execute('PRAGMA foreign_keys=ON')
            
            self.logger.debug(f"线程 {threading.current_thread().name} 创建数据库连接")
        
        return self.local.conn
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self.local, 'conn') and self.local.conn is not None:
            self.local.conn.close()
            self.local.conn = None
            self.logger.debug(f"线程 {threading.current_thread().name} 关闭数据库连接")
    
    def init_database(self):
        """初始化数据库，创建所有必要的表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 表1: 股票列表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_list (
                    ts_code TEXT PRIMARY KEY,
                    name TEXT,
                    market TEXT,
                    list_date TEXT,
                    delist_date TEXT,
                    is_st INTEGER DEFAULT 0,
                    update_time TEXT
                )
            ''')
            
            # 表2: 资产负债表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS balancesheet (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    ann_date TEXT,
                    data_json TEXT NOT NULL,
                    update_flag INTEGER,
                    update_time TEXT,
                    UNIQUE(ts_code, end_date)
                )
            ''')
            
            # 表3: 利润表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS income (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    ann_date TEXT,
                    data_json TEXT NOT NULL,
                    update_flag INTEGER,
                    update_time TEXT,
                    UNIQUE(ts_code, end_date)
                )
            ''')
            
            # 表4: 现金流量表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cashflow (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    ann_date TEXT,
                    data_json TEXT NOT NULL,
                    update_flag INTEGER,
                    update_time TEXT,
                    UNIQUE(ts_code, end_date)
                )
            ''')
            
            # 表5: 财务指标
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fina_indicator (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    ann_date TEXT,
                    data_json TEXT NOT NULL,
                    update_flag INTEGER,
                    update_time TEXT,
                    UNIQUE(ts_code, end_date)
                )
            ''')
            
            # 表6: 四大核心指标
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS core_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    
                    -- 指标1: 报表逻辑一致性检验
                    ar_turnover_log REAL,
                    gross_margin REAL,
                    
                    -- 指标2: 再投资质量
                    lta_turnover_log REAL,
                    
                    -- 指标3: 产业链地位
                    working_capital_ratio REAL,
                    
                    -- 指标4: 真实盈利水平
                    ocf_ratio REAL,
                    
                    -- 分位数数据
                    ar_turnover_log_percentile REAL,
                    gross_margin_percentile REAL,
                    lta_turnover_log_percentile REAL,
                    working_capital_ratio_percentile REAL,
                    ocf_ratio_percentile REAL,
                    
                    -- 元数据
                    data_complete INTEGER DEFAULT 1,
                    update_time TEXT,
                    
                    UNIQUE(ts_code, end_date)
                )
            ''')
            
            # 表7: 全A股分布统计
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_distribution (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    end_date TEXT NOT NULL,
                    indicator_name TEXT NOT NULL,
                    
                    -- 分布统计
                    count INTEGER,
                    mean REAL,
                    median REAL,
                    std REAL,
                    min REAL,
                    max REAL,
                    p25 REAL,
                    p75 REAL,
                    
                    -- 完整分位数数据（JSON格式，0-100）
                    percentiles_json TEXT,
                    
                    update_time TEXT,
                    
                    UNIQUE(end_date, indicator_name)
                )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_balancesheet_ts_code ON balancesheet(ts_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_balancesheet_end_date ON balancesheet(end_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_ts_code ON income(ts_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_end_date ON income(end_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cashflow_ts_code ON cashflow(ts_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cashflow_end_date ON cashflow(end_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fina_indicator_ts_code ON fina_indicator(ts_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fina_indicator_end_date ON fina_indicator(end_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_core_indicators_ts_code ON core_indicators(ts_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_core_indicators_end_date ON core_indicators(end_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_distribution_end_date ON market_distribution(end_date)')
            
            conn.commit()
            self.logger.info("数据库初始化完成")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"数据库初始化失败: {e}")
            raise
    
    # ========================================================================
    # 股票列表管理
    # ========================================================================
    
    def add_stock(self, ts_code: str, name: str, market: str, 
                  list_date: str, delist_date: str = None, is_st: int = 0):
        """
        添加或更新股票信息
        
        Args:
            ts_code: 股票代码
            name: 股票名称
            market: 市场（主板/创业板/科创板）
            list_date: 上市日期
            delist_date: 退市日期
            is_st: 是否ST股票
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO stock_list 
                (ts_code, name, market, list_date, delist_date, is_st, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (ts_code, name, market, list_date, delist_date, is_st, 
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"添加股票 {ts_code} 失败: {e}")
            raise
    
    def get_all_stocks(self, exclude_st: bool = False, 
                       exclude_delisted: bool = True) -> List[Dict]:
        """
        获取所有股票列表
        
        Args:
            exclude_st: 是否排除ST股票
            exclude_delisted: 是否排除已退市股票
            
        Returns:
            股票列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM stock_list WHERE 1=1'
        
        if exclude_st:
            query += ' AND is_st = 0'
        
        if exclude_delisted:
            query += ' AND (delist_date IS NULL OR delist_date = "")'
        
        cursor.execute(query)
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        return results
    
    # ========================================================================
    # 财务数据管理
    # ========================================================================
    
    def save_financial_data(self, ts_code: str, end_date: str, 
                           data_type: str, data: pd.DataFrame,
                           update_flag: int = None):
        """
        保存财务数据（线程安全）
        
        Args:
            ts_code: 股票代码
            end_date: 报告期
            data_type: 数据类型（balancesheet/income/cashflow/fina_indicator）
            data: 财务数据DataFrame
            update_flag: 更新标识
        """
        if data_type not in ['balancesheet', 'income', 'cashflow', 'fina_indicator']:
            raise ValueError(f"不支持的数据类型: {data_type}")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 处理重复列名：保留第一个，删除后续重复的
        data_clean = data.copy()
        if data_clean.columns.duplicated().any():
            # 找到重复的列
            duplicated_cols = data_clean.columns[data_clean.columns.duplicated()].tolist()
            self.logger.warning(f"发现重复列名: {duplicated_cols}，将保留第一个")
            
            # 去除重复列（保留第一个）
            data_clean = data_clean.loc[:, ~data_clean.columns.duplicated()]
        
        # 将DataFrame转换为JSON
        data_json = data_clean.to_json(orient='records', force_ascii=False)
        
        # 提取公告日期
        ann_date = None
        if 'ann_date' in data.columns and len(data) > 0:
            ann_date = str(data['ann_date'].iloc[0]) if pd.notna(data['ann_date'].iloc[0]) else None
        
        try:
            # 使用 BEGIN IMMEDIATE 立即获取写锁
            cursor.execute('BEGIN IMMEDIATE')
            
            cursor.execute(f'''
                INSERT OR REPLACE INTO {data_type}
                (ts_code, end_date, ann_date, data_json, update_flag, update_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ts_code, end_date, ann_date, data_json, update_flag,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower():
                # 数据库锁定，等待后重试
                conn.rollback()
                import time
                time.sleep(0.1)
                return self.save_financial_data(ts_code, end_date, data_type, data, update_flag)
            else:
                conn.rollback()
                self.logger.error(f"保存 {data_type} 数据失败 ({ts_code}, {end_date}): {e}")
                raise
        except Exception as e:
            conn.rollback()
            self.logger.error(f"保存 {data_type} 数据失败 ({ts_code}, {end_date}): {e}")
            raise
    
    def get_financial_data(self, ts_code: str, data_type: str,
                          start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取财务数据
        
        Args:
            ts_code: 股票代码
            data_type: 数据类型
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            财务数据DataFrame
        """
        if data_type not in ['balancesheet', 'income', 'cashflow', 'fina_indicator']:
            raise ValueError(f"不支持的数据类型: {data_type}")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = f'SELECT data_json FROM {data_type} WHERE ts_code = ?'
        params = [ts_code]
        
        if start_date:
            query += ' AND end_date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND end_date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY end_date'
        
        cursor.execute(query, params)
        
        all_data = []
        for row in cursor.fetchall():
            data_json = row[0]
            data = pd.read_json(StringIO(data_json), orient='records')
            all_data.append(data)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def check_data_exists(self, ts_code: str, end_date: str, data_type: str) -> bool:
        """
        检查数据是否已存在
        
        Args:
            ts_code: 股票代码
            end_date: 报告期
            data_type: 数据类型
            
        Returns:
            是否存在
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT COUNT(*) FROM {data_type}
            WHERE ts_code = ? AND end_date = ?
        ''', (ts_code, end_date))
        
        count = cursor.fetchone()[0]
        return count > 0
    
    # ========================================================================
    # 核心指标管理
    # ========================================================================
    
    def save_core_indicators(self, ts_code: str, end_date: str, 
                            indicators: Dict[str, float],
                            data_complete: int = 1):
        """
        保存四大核心指标
        
        Args:
            ts_code: 股票代码
            end_date: 报告期
            indicators: 指标字典
            data_complete: 数据完整性标识
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('BEGIN IMMEDIATE')
            
            cursor.execute('''
                INSERT OR REPLACE INTO core_indicators
                (ts_code, end_date, ar_turnover_log, gross_margin, lta_turnover_log,
                 working_capital_ratio, ocf_ratio, ar_turnover_log_percentile,
                 gross_margin_percentile, lta_turnover_log_percentile,
                 working_capital_ratio_percentile, ocf_ratio_percentile,
                 data_complete, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ts_code, end_date,
                indicators.get('ar_turnover_log'),
                indicators.get('gross_margin'),
                indicators.get('lta_turnover_log'),
                indicators.get('working_capital_ratio'),
                indicators.get('ocf_ratio'),
                indicators.get('ar_turnover_log_percentile'),
                indicators.get('gross_margin_percentile'),
                indicators.get('lta_turnover_log_percentile'),
                indicators.get('working_capital_ratio_percentile'),
                indicators.get('ocf_ratio_percentile'),
                data_complete,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower():
                conn.rollback()
                import time
                time.sleep(0.1)
                return self.save_core_indicators(ts_code, end_date, indicators, data_complete)
            else:
                conn.rollback()
                raise
        except Exception as e:
            conn.rollback()
            self.logger.error(f"保存核心指标失败 ({ts_code}, {end_date}): {e}")
            raise
    
    def get_core_indicators(self, ts_code: str, 
                           start_date: str = None, 
                           end_date: str = None) -> pd.DataFrame:
        """
        获取核心指标数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            核心指标DataFrame
        """
        conn = self.get_connection()
        
        query = 'SELECT * FROM core_indicators WHERE ts_code = ?'
        params = [ts_code]
        
        if start_date:
            query += ' AND end_date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND end_date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY end_date'
        
        return pd.read_sql_query(query, conn, params=params)
    
    # ========================================================================
    # 市场分布数据管理
    # ========================================================================
    
    def save_market_distribution(self, end_date: str, indicator_name: str,
                                 distribution: Dict[str, Any]):
        """
        保存全A股分布统计数据
        
        Args:
            end_date: 报告期
            indicator_name: 指标名称
            distribution: 分布统计数据
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 将分位数数据转换为JSON
        percentiles_json = json.dumps(distribution.get('percentiles', {}))
        
        try:
            cursor.execute('BEGIN IMMEDIATE')
            
            cursor.execute('''
                INSERT OR REPLACE INTO market_distribution
                (end_date, indicator_name, count, mean, median, std, min, max,
                 p25, p75, percentiles_json, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                end_date, indicator_name,
                distribution.get('count'),
                distribution.get('mean'),
                distribution.get('median'),
                distribution.get('std'),
                distribution.get('min'),
                distribution.get('max'),
                distribution.get('p25'),
                distribution.get('p75'),
                percentiles_json,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower():
                conn.rollback()
                import time
                time.sleep(0.1)
                return self.save_market_distribution(end_date, indicator_name, distribution)
            else:
                conn.rollback()
                raise
        except Exception as e:
            conn.rollback()
            self.logger.error(f"保存市场分布数据失败 ({end_date}, {indicator_name}): {e}")
            raise
    
    def get_market_distribution(self, end_date: str, indicator_name: str) -> Dict:
        """
        获取市场分布数据
        
        Args:
            end_date: 报告期
            indicator_name: 指标名称
            
        Returns:
            分布统计数据
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM market_distribution
            WHERE end_date = ? AND indicator_name = ?
        ''', (end_date, indicator_name))
        
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))
            
            # 解析JSON
            if result.get('percentiles_json'):
                result['percentiles'] = json.loads(result['percentiles_json'])
            
            return result
        else:
            return None
    
    # ========================================================================
    # 工具方法
    # ========================================================================
    
    def get_database_stats(self) -> Dict[str, int]:
        """
        获取数据库统计信息
        
        Returns:
            各表的记录数
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        tables = ['stock_list', 'balancesheet', 'income', 'cashflow', 
                 'fina_indicator', 'core_indicators', 'market_distribution']
        
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[table] = cursor.fetchone()[0]
        
        return stats
    
    def vacuum_database(self):
        """优化数据库，回收空间"""
        conn = self.get_connection()
        conn.execute('VACUUM')
        self.logger.info("数据库优化完成")


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == '__main__':
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 初始化数据库
    db_manager = FinancialDataManager('database/financial_data_test.db')
    
    print("\n数据库初始化完成")
    
    # 测试添加股票
    db_manager.add_stock(
        ts_code='000333.SZ',
        name='美的集团',
        market='主板',
        list_date='20130923',
        is_st=0
    )
    
    print("✓ 添加股票成功")
    
    # 测试获取股票列表
    stocks = db_manager.get_all_stocks()
    print(f"✓ 股票列表: {len(stocks)} 只")
    
    # 测试保存财务数据
    test_data = pd.DataFrame({
        'end_date': ['20231231'],
        'ann_date': ['20240430'],
        'total_assets': [1000000],
        'total_liab': [500000]
    })
    
    db_manager.save_financial_data(
        ts_code='000333.SZ',
        end_date='20231231',
        data_type='balancesheet',
        data=test_data
    )
    
    print("✓ 保存财务数据成功")
    
    # 测试获取财务数据
    data = db_manager.get_financial_data('000333.SZ', 'balancesheet')
    print(f"✓ 获取财务数据: {len(data)} 条记录")
    
    # 测试保存核心指标
    indicators = {
        'ar_turnover_log': 2.45,
        'gross_margin': 0.285,
        'lta_turnover_log': 1.87,
        'working_capital_ratio': -0.152,
        'ocf_ratio': 0.123,
        'ar_turnover_log_percentile': 75.0,
        'gross_margin_percentile': 68.0
    }
    
    db_manager.save_core_indicators('000333.SZ', '20231231', indicators)
    print("✓ 保存核心指标成功")
    
    # 测试获取核心指标
    core_data = db_manager.get_core_indicators('000333.SZ')
    print(f"✓ 获取核心指标: {len(core_data)} 条记录")
    
    # 获取数据库统计
    stats = db_manager.get_database_stats()
    print("\n数据库统计:")
    for table, count in stats.items():
        print(f"  {table}: {count} 条记录")
    
    print("\n✓ 所有测试通过！")
