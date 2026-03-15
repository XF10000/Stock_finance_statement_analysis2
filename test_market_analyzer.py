"""
测试市场分析器
"""

import logging
import pandas as pd
from market_data_manager import MarketDataManager
from market_analyzer import MarketAnalyzer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_market_analyzer():
    """测试市场分析器"""
    
    print("="*80)
    print("测试市场分析器")
    print("="*80)
    
    # 初始化
    db = MarketDataManager('database/market_data_test.db')
    analyzer = MarketAnalyzer(db)
    
    # 1. 分析所有报告期
    print("\n1. 分析所有报告期的市场分布...")
    print("-"*80)
    
    results = analyzer.analyze_all_periods(
        exclude_outliers=True,
        outlier_std=3.0
    )
    
    print(f"\n✓ 成功分析 {len(results)} 个报告期")
    
    # 显示部分结果
    if results:
        print("\n最近5个报告期的更新情况:")
        for period, count in list(results.items())[-5:]:
            print(f"  {period}: 更新 {count} 只股票")
    
    # 2. 查看某个报告期的市场分布
    print("\n\n2. 查看最新报告期的市场分布...")
    print("-"*80)
    
    if results:
        latest_period = list(results.keys())[-1]
        market_stats = analyzer.calculate_market_percentiles(latest_period)
        
        print(f"\n报告期: {latest_period}")
        print(f"{'指标':<30} {'样本数':>8} {'均值':>10} {'中位数':>10} {'25%':>10} {'75%':>10}")
        print("-"*80)
        
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
                print(f"{name:<30} {stats['count']:>8} {stats['mean']:>10.2f} "
                      f"{stats['p50']:>10.2f} {stats['p25']:>10.2f} {stats['p75']:>10.2f}")
    
    # 3. 查看单只股票的分位数历史
    print("\n\n3. 查看贵州茅台的分位数历史...")
    print("-"*80)
    
    ts_code = '600519.SH'
    history = analyzer.get_stock_percentile_history(ts_code)
    
    if len(history) > 0:
        print(f"\n✓ 找到 {len(history)} 期数据")
        print("\n最近5期的分位数排名:")
        print(f"{'报告期':>10} {'应收周转率%':>12} {'毛利率%':>10} "
              f"{'长期资产周转%':>14} {'净营运资本%':>12} {'经营现金流%':>12}")
        print("-"*80)
        
        recent = history.tail(5)
        for _, row in recent.iterrows():
            def fmt(val):
                return f"{val:>12.1f}" if pd.notna(val) else f"{'N/A':>12}"
            
            print(f"{int(row['end_date']):>10} "
                  f"{fmt(row['ar_turnover_log_percentile'])} "
                  f"{fmt(row['gross_margin_percentile'])} "
                  f"{fmt(row['lta_turnover_log_percentile'])} "
                  f"{fmt(row['working_capital_ratio_percentile'])} "
                  f"{fmt(row['ocf_ratio_percentile'])}")
    else:
        print("  未找到数据")
    
    # 4. 查看某个指标的历史市场分布
    print("\n\n4. 查看毛利率的历史市场分布...")
    print("-"*80)
    
    dist_history = analyzer.get_market_distribution_history('gross_margin')
    
    if len(dist_history) > 0:
        print(f"\n✓ 找到 {len(dist_history)} 期数据")
        print("\n最近5期的市场分布:")
        print(f"{'报告期':>10} {'样本数':>8} {'均值':>10} {'中位数':>10} {'25%':>10} {'75%':>10}")
        print("-"*80)
        
        recent = dist_history.tail(5)
        for _, row in recent.iterrows():
            print(f"{int(row['end_date']):>10} {int(row['count']):>8} "
                  f"{row['mean']:>10.2f} {row['p50']:>10.2f} "
                  f"{row['p25']:>10.2f} {row['p75']:>10.2f}")
    else:
        print("  未找到数据")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == '__main__':
    test_market_analyzer()
