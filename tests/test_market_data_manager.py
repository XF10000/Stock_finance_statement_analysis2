"""
测试 MarketDataManager 数据库管理器
"""
import pytest
import pandas as pd
from datetime import datetime


class TestMarketDataManager:
    """测试数据库管理器基础功能"""
    
    def test_init_database(self, db_manager):
        """测试数据库初始化"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # 检查核心表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('balancesheet', 'income', 'cashflow', 'core_indicators')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'balancesheet' in tables
        assert 'income' in tables
        assert 'cashflow' in tables
        assert 'core_indicators' in tables
    
    def test_save_and_get_financial_data(self, db_manager):
        """测试保存和读取财务数据"""
        test_data = {
            'ts_code': '000001.SZ',
            'end_date': '20231231',
            'total_assets': 1000000,
            'total_liab': 600000
        }
        
        # 保存数据
        db_manager.save_financial_data(
            ts_code='000001.SZ',
            table_name='balancesheet',
            data=test_data
        )
        
        # 读取数据
        result = db_manager.get_financial_data('000001.SZ', 'balancesheet')
        
        assert len(result) == 1
        assert result.iloc[0]['ts_code'] == '000001.SZ'
        assert result.iloc[0]['end_date'] == '20231231'
        assert result.iloc[0]['total_assets'] == 1000000
    
    def test_save_core_indicators(self, db_manager):
        """测试保存核心指标"""
        indicators = {
            'ar_turnover_log': 2.5,
            'gross_margin': 30.5,
            'lta_turnover_log': 1.8,
            'working_capital_ratio': 0.5,
            'ocf_ratio': 5.2
        }
        
        db_manager.save_core_indicators(
            ts_code='000001.SZ',
            end_date='20231231',
            indicators=indicators,
            data_complete=1
        )
        
        # 验证数据
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ar_turnover_log, gross_margin, lta_turnover_log, 
                   working_capital_ratio, ocf_ratio
            FROM core_indicators
            WHERE ts_code = ? AND end_date = ?
        """, ('000001.SZ', '20231231'))
        
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 2.5
        assert row[1] == 30.5
        assert row[2] == 1.8
        assert row[3] == 0.5
        assert row[4] == 5.2
    
    def test_get_stock_list(self, populated_db):
        """测试获取股票列表"""
        stocks = populated_db.get_stock_list()
        
        assert len(stocks) > 0
        assert '000001.SZ' in [s[0] for s in stocks]
    
    def test_data_update_with_duplicate(self, db_manager):
        """测试重复数据更新（INSERT OR REPLACE）"""
        test_data = {
            'ts_code': '000001.SZ',
            'end_date': '20231231',
            'total_assets': 1000000
        }
        
        # 第一次保存
        db_manager.save_financial_data('000001.SZ', 'balancesheet', test_data)
        
        # 更新数据
        test_data['total_assets'] = 1200000
        db_manager.save_financial_data('000001.SZ', 'balancesheet', test_data)
        
        # 验证只有一条记录且值已更新
        result = db_manager.get_financial_data('000001.SZ', 'balancesheet')
        assert len(result) == 1
        assert result.iloc[0]['total_assets'] == 1200000


class TestMarketDataManagerThreadSafety:
    """测试多线程安全性"""
    
    def test_concurrent_writes(self, db_manager):
        """测试并发写入（简单验证）"""
        import threading
        
        def write_data(ts_code, end_date):
            db_manager.save_financial_data(
                ts_code=ts_code,
                table_name='balancesheet',
                data={
                    'ts_code': ts_code,
                    'end_date': end_date,
                    'total_assets': 1000000
                }
            )
        
        threads = []
        for i in range(5):
            t = threading.Thread(
                target=write_data,
                args=(f'00000{i}.SZ', '20231231')
            )
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证所有数据都已写入
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM balancesheet")
        count = cursor.fetchone()[0]
        assert count == 5
