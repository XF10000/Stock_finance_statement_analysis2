"""
pytest 配置文件和共享 fixtures
"""
import pytest
import sqlite3
import os
import tempfile
import pandas as pd
from datetime import datetime


@pytest.fixture(scope="function")
def test_db_path():
    """创建临时测试数据库"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # 清理
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="function")
def db_manager(test_db_path):
    """创建数据库管理器实例"""
    from financial_data_manager import FinancialDataManager
    manager = FinancialDataManager(test_db_path)
    yield manager
    # 每个测试后清理连接
    if hasattr(manager.local, 'conn') and manager.local.conn:
        manager.local.conn.close()


@pytest.fixture(scope="function")
def sample_balance_data():
    """示例资产负债表数据"""
    return pd.DataFrame({
        'ts_code': ['000001.SZ'] * 4,
        'end_date': ['20231231', '20230930', '20230630', '20230331'],
        'total_assets': [1000000, 950000, 900000, 850000],
        'total_liab': [600000, 570000, 540000, 510000],
        'total_cur_assets': [400000, 380000, 360000, 340000],
        'total_cur_liab': [300000, 285000, 270000, 255000],
        'fix_assets': [500000, 480000, 460000, 440000],
        'accounts_receiv': [100000, 95000, 90000, 85000],
    })


@pytest.fixture(scope="function")
def sample_income_data():
    """示例利润表数据"""
    return pd.DataFrame({
        'ts_code': ['000001.SZ'] * 4,
        'end_date': ['20231231', '20230930', '20230630', '20230331'],
        'revenue': [500000, 375000, 250000, 125000],
        'oper_cost': [300000, 225000, 150000, 75000],
        'operate_profit': [150000, 112500, 75000, 37500],
        'total_profit': [140000, 105000, 70000, 35000],
        'n_income': [120000, 90000, 60000, 30000],
    })


@pytest.fixture(scope="function")
def sample_cashflow_data():
    """示例现金流量表数据"""
    return pd.DataFrame({
        'ts_code': ['000001.SZ'] * 4,
        'end_date': ['20231231', '20230930', '20230630', '20230331'],
        'n_cashflow_act': [80000, 60000, 40000, 20000],
        'n_cashflow_inv_act': [-30000, -22500, -15000, -7500],
        'n_cash_flows_fnc_act': [-20000, -15000, -10000, -5000],
    })


@pytest.fixture(scope="function")
def populated_db(db_manager, sample_balance_data, sample_income_data, sample_cashflow_data):
    """填充了示例数据的数据库"""
    # 添加测试股票到 stock_list
    db_manager.add_stock('000001.SZ', '平安银行', '主板', '19910403')
    
    # 保存资产负债表数据（按报告期逐条保存）
    for _, row in sample_balance_data.iterrows():
        db_manager.save_financial_data(
            ts_code=row['ts_code'],
            end_date=str(row['end_date']),
            data_type='balancesheet',
            data=pd.DataFrame([row.to_dict()])
        )
    
    # 保存利润表数据
    for _, row in sample_income_data.iterrows():
        db_manager.save_financial_data(
            ts_code=row['ts_code'],
            end_date=str(row['end_date']),
            data_type='income',
            data=pd.DataFrame([row.to_dict()])
        )
    
    # 保存现金流量表数据
    for _, row in sample_cashflow_data.iterrows():
        db_manager.save_financial_data(
            ts_code=row['ts_code'],
            end_date=str(row['end_date']),
            data_type='cashflow',
            data=pd.DataFrame([row.to_dict()])
        )
    
    return db_manager
