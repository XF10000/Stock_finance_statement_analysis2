#!/usr/bin/env python3
"""
重新计算单只股票的核心指标
"""
import sys
import pandas as pd
from datetime import datetime
from financial_data_manager import FinancialDataManager
from core_indicators_analyzer import CoreIndicatorsAnalyzer

def normalize_ts_code(ts_code: str) -> str:
    """
    规范化股票代码，自动添加交易所后缀
    
    Args:
        ts_code: 股票代码（可以是6位数字或带后缀的完整代码）
        
    Returns:
        规范化后的股票代码（带交易所后缀）
    """
    # 如果已经有后缀，直接返回
    if '.' in ts_code:
        return ts_code.upper()
    
    # 补全代码到6位数字
    code = ts_code.zfill(6)
    
    # 根据代码开头判断交易所
    # 深圳：000、002、003、300开头
    # 上海：600、601、603、605、688开头
    if code.startswith(('000', '002', '003', '300')):
        return f"{code}.SZ"
    elif code.startswith(('600', '601', '603', '605', '688')):
        return f"{code}.SH"
    else:
        # 默认深圳（兼容其他代码）
        return f"{code}.SZ"


if len(sys.argv) < 2:
    print("用法: python3 recalc_single_stock.py <股票代码>")
    sys.exit(1)

ts_code = normalize_ts_code(sys.argv[1])

print(f"重新计算 {ts_code} 的核心指标...")

db = FinancialDataManager('database/financial_data.db')
analyzer = CoreIndicatorsAnalyzer()

# 读取财务数据
balance = db.get_financial_data(ts_code, 'balancesheet')
income = db.get_financial_data(ts_code, 'income')
cashflow = db.get_financial_data(ts_code, 'cashflow')

if len(balance) == 0 or len(income) == 0 or len(cashflow) == 0:
    print(f"✗ 缺少财务数据")
    sys.exit(1)

# 计算指标
indicators = analyzer.calculate_all_indicators(balance, income, cashflow)

if len(indicators) == 0:
    print(f"✗ 计算结果为空")
    sys.exit(1)

print(f"✓ 计算出 {len(indicators)} 个季度的指标")

# 删除旧数据
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("DELETE FROM core_indicators WHERE ts_code=?", (ts_code,))
conn.commit()

# 批量保存
insert_data = []
for _, row in indicators.iterrows():
    end_date = row.get('报告期')
    if isinstance(end_date, str):
        end_date = end_date.replace('-', '')
    
    ar_turnover_log = row.get('应收账款周转率对数')
    gross_margin = row.get('毛利率')
    lta_turnover_log = row.get('长期经营资产周转率对数')
    working_capital_ratio = row.get('净营运资本比率')
    ocf_ratio = row.get('经营现金流比率')
    
    # 检查是否至少有一个有效指标值
    has_valid_data = any(
        pd.notna(v) for v in [ar_turnover_log, gross_margin, lta_turnover_log, working_capital_ratio, ocf_ratio]
    )
    
    if has_valid_data:
        insert_data.append((
            ts_code,
            str(int(end_date)),
            ar_turnover_log,
            gross_margin,
            lta_turnover_log,
            working_capital_ratio,
            ocf_ratio,
            None, None, None, None, None,  # percentiles
            1,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))

cursor.executemany('''
    INSERT INTO core_indicators (
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

print(f"✓ 保存 {len(insert_data)} 条记录")

# 更新分位数
from financial_data_analyzer import FinancialDataAnalyzer
analyzer_market = FinancialDataAnalyzer(db)

quarters = [str(int(row['报告期'])) for _, row in indicators.iterrows()]
total_updated = 0
for end_date in quarters:
    count = analyzer_market.update_percentile_ranks(end_date)
    total_updated += count

print(f"✓ 更新分位数: {total_updated} 条记录")
print(f"\n完成！")
