"""重新计算单只股票的核心指标"""
import sys
from market_data_manager import MarketDataManager
from core_indicators_analyzer import CoreIndicatorsAnalyzer

ts_code = sys.argv[1] if len(sys.argv) > 1 else '000333.SZ'

print(f"重新计算 {ts_code} 的核心指标...")

db = MarketDataManager('database/market_data.db')
analyzer = CoreIndicatorsAnalyzer()

# 获取财务数据
balance = db.get_financial_data(ts_code, 'balancesheet')
income = db.get_financial_data(ts_code, 'income')
cashflow = db.get_financial_data(ts_code, 'cashflow')

# 计算指标
indicators = analyzer.calculate_all_indicators(balance, income, cashflow)

print(f"计算完成，共 {len(indicators)} 个报告期")

# 保存到数据库
conn = db.get_connection()
cursor = conn.cursor()

# 先删除旧数据
cursor.execute('DELETE FROM core_indicators WHERE ts_code = ?', (ts_code,))
conn.commit()

# 批量插入新数据
for _, row in indicators.iterrows():
    indicator_dict = row.to_dict()
    # 移除报告期字段，因为save_core_indicators会单独处理
    end_date = indicator_dict.pop('报告期')
    db.save_core_indicators(ts_code, end_date, indicator_dict)

print(f"✓ 已保存到数据库")

# 显示最近几个报告期的数据
print(f"\n最近报告期的长期资产周转率对数：")
print(f"{'报告期':<12} {'长期资产周转率对数':>20}")
print("-" * 35)

recent = indicators[indicators['报告期'] >= 20240000].sort_values('报告期')
for _, row in recent.iterrows():
    period = int(row['报告期'])
    lta_log = row.get('长期经营资产周转率对数', float('nan'))
    print(f"{period:<12} {lta_log:>20.4f}")
