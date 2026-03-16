"""
批量计算100只A股的核心指标并更新市场分布（测试版）
"""

import logging
from market_data_manager import MarketDataManager
from core_indicators_analyzer import CoreIndicatorsAnalyzer
from market_analyzer import MarketAnalyzer
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.WARNING,  # 只显示警告和错误
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    print("="*80)
    print("批量计算100只A股的核心指标（测试）")
    print("="*80)
    
    db = MarketDataManager('database/market_data.db')
    analyzer = CoreIndicatorsAnalyzer()
    
    # 获取前100只股票
    import sqlite3
    conn = sqlite3.connect('database/market_data.db')
    cursor = conn.cursor()
    
    stocks = cursor.execute("SELECT ts_code, name FROM stock_list ORDER BY ts_code LIMIT 100").fetchall()
    conn.close()
    
    total_stocks = len(stocks)
    print(f"\n测试股票数: {total_stocks} 只")
    
    success_count = 0
    failed_count = 0
    failed_stocks = []
    
    print("\n开始计算核心指标...")
    
    for ts_code, name in tqdm(stocks, desc="计算进度"):
        try:
            # 获取财务数据
            balance = db.get_financial_data(ts_code, 'balancesheet')
            income = db.get_financial_data(ts_code, 'income')
            cashflow = db.get_financial_data(ts_code, 'cashflow')
            
            if balance is None or income is None or cashflow is None:
                failed_count += 1
                failed_stocks.append((ts_code, name, "数据不完整"))
                continue
            
            # 计算指标
            indicators = analyzer.calculate_all_indicators(balance, income, cashflow)
            
            if len(indicators) == 0:
                failed_count += 1
                failed_stocks.append((ts_code, name, "指标计算失败"))
                continue
            
            # 保存到数据库
            saved_count = 0
            for _, row in indicators.iterrows():
                indicator_dict = {
                    'ar_turnover_log': row.get('应收账款周转率对数'),
                    'gross_margin': row.get('毛利率'),
                    'lta_turnover_log': row.get('长期经营资产周转率对数'),
                    'working_capital_ratio': row.get('净营运资本比率'),
                    'ocf_ratio': row.get('经营现金流比率')
                }
                
                db.save_core_indicators(
                    ts_code=ts_code,
                    end_date=str(int(row['报告期'])),
                    indicators=indicator_dict
                )
                saved_count += 1
            
            success_count += 1
            
        except Exception as e:
            failed_count += 1
            failed_stocks.append((ts_code, name, str(e)[:50]))
            continue
    
    print(f"\n计算完成！")
    print(f"  成功: {success_count} 只")
    print(f"  失败: {failed_count} 只")
    
    if len(failed_stocks) > 0:
        print(f"\n失败的股票（前10只）:")
        for ts_code, name, reason in failed_stocks[:10]:
            print(f"  {ts_code} {name}: {reason}")
    
    # 重新计算市场分布
    print("\n" + "="*80)
    print("重新计算市场分布")
    print("="*80)
    
    market_analyzer = MarketAnalyzer(db)
    results = market_analyzer.analyze_all_periods(exclude_outliers=True)
    
    print(f"\n✓ 成功分析 {len(results)} 个报告期的市场分布")
    
    # 显示最新报告期的市场分布
    if len(results) > 0:
        latest_period = list(results.keys())[-1]
        market_stats = market_analyzer.calculate_market_percentiles(latest_period)
        
        print(f"\n最新报告期 ({latest_period}) 市场分布:")
        print(f"  {'指标':<30} {'样本数':>8} {'均值':>10} {'中位数':>10}")
        print("  " + "-"*60)
        
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
                print(f"  {name:<30} {stats['count']:>8} {stats['mean']:>10.2f} {stats['p50']:>10.2f}")
        
        # 检查毛利率是否合理
        if 'gross_margin' in market_stats:
            median = market_stats['gross_margin']['p50']
            if 20 <= median <= 40:
                print(f"\n✓ 毛利率中位数 {median:.2f}% 在合理范围内（20-40%）")
            else:
                print(f"\n⚠️  毛利率中位数 {median:.2f}% 可能不合理")
    
    print("\n" + "="*80)
    print("测试完成！如果结果正常，可以运行 calculate_all_indicators.py 计算全部股票")
    print("="*80)


if __name__ == '__main__':
    main()
