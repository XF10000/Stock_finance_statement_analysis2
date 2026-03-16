"""重新计算2025Q3的市场分布"""
from market_data_manager import MarketDataManager
from market_analyzer import MarketAnalyzer

db = MarketDataManager('database/market_data.db')
analyzer = MarketAnalyzer(db)

print("="*80)
print("重新计算2025Q3市场分布")
print("="*80)

# 计算2025Q3的市场分位数
market_stats = analyzer.calculate_market_percentiles('20250930', exclude_outliers=True)

print(f"\n计算结果：")
print(f"  {'指标':<30} {'样本数':>8} {'中位数':>10}")
print("  " + "-"*50)

indicator_names = {
    'ar_turnover_log': '应收账款周转率对数',
    'gross_margin': '毛利率',
    'lta_turnover_log': '长期经营资产周转率对数',
    'working_capital_ratio': '净营运资本比率',
    'ocf_ratio': '经营现金流比率'
}

for col, name in indicator_names.items():
    if col in market_stats:
        stats = market_stats[col]
        print(f"  {name:<30} {stats['count']:>8} {stats['p50']:>10.2f}")
    else:
        print(f"  {name:<30} {'缺失':>8} {'N/A':>10}")

# 保存到数据库
if market_stats:
    print("\n保存市场分布到数据库...")
    analyzer.save_market_distribution('20250930', market_stats)
    print("✓ 保存成功")
    
    # 更新分位数排名
    print("\n更新分位数排名...")
    updated_count = analyzer.update_percentile_ranks('20250930', market_stats)
    print(f"✓ 更新了 {updated_count} 只股票的分位数排名")

print("\n" + "="*80)
print("完成！")
print("="*80)
