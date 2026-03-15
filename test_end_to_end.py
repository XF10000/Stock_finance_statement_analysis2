"""
端到端完整测试：从API获取到数据库写入的完整流程
"""

import logging
import os
import sqlite3
from datetime import datetime
from update_market_data import MarketDataUpdater
from core_indicators_analyzer import CoreIndicatorsAnalyzer
from market_analyzer import MarketAnalyzer
from market_data_manager import MarketDataManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 测试数据库路径
TEST_DB = 'database/test_end_to_end.db'


def test_full_pipeline():
    """测试完整的数据流程"""
    
    print("="*80)
    print("端到端完整测试")
    print("="*80)
    
    # 清理旧的测试数据库
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        print(f"✓ 已清理旧测试数据库")
    
    # 测试股票列表
    test_stocks = [
        '600519.SH',  # 贵州茅台
        '000333.SZ',  # 美的集团
        '000858.SZ',  # 五粮液
    ]
    
    print(f"\n测试股票: {', '.join(test_stocks)}")
    print("="*80)
    
    # ========================================================================
    # 阶段1: 从Tushare API获取数据
    # ========================================================================
    print("\n【阶段1】从Tushare API获取数据")
    print("-"*80)
    
    updater = MarketDataUpdater(
        config_path='config.yaml',
        db_path=TEST_DB,
        max_workers=1  # 单线程
    )
    
    # 获取股票列表
    all_stocks = updater.get_all_a_stocks(exclude_bse=True)
    test_stock_dicts = [s for s in all_stocks if s['ts_code'] in test_stocks]
    
    print(f"1.1 获取股票列表: ✓ {len(test_stock_dicts)} 只")
    
    # 逐只获取数据
    for stock in test_stock_dicts:
        ts_code = stock['ts_code']
        print(f"\n1.2 获取 {ts_code} 的数据...")
        
        success = updater.fetch_stock_all_data(ts_code, force_update=True)
        
        if success:
            print(f"  ✓ {ts_code} 数据获取成功")
        else:
            print(f"  ✗ {ts_code} 数据获取失败")
            return False
    
    print("\n✓ 阶段1完成：所有数据已从API获取")
    
    # ========================================================================
    # 阶段2: 验证数据库写入
    # ========================================================================
    print("\n【阶段2】验证数据库写入")
    print("-"*80)
    
    db = MarketDataManager(TEST_DB)
    
    # 检查数据库统计
    stats = db.get_database_stats()
    print("\n2.1 数据库统计:")
    for table, count in stats.items():
        print(f"  {table}: {count} 条记录")
    
    # 验证每只股票的数据
    print("\n2.2 验证各股票数据完整性:")
    for ts_code in test_stocks:
        balance = db.get_financial_data(ts_code, 'balancesheet')
        income = db.get_financial_data(ts_code, 'income')
        cashflow = db.get_financial_data(ts_code, 'cashflow')
        fina = db.get_financial_data(ts_code, 'fina_indicator')
        
        if balance is None or income is None or cashflow is None or fina is None:
            print(f"  ✗ {ts_code}: 数据不完整")
            return False
        
        print(f"  ✓ {ts_code}: 资产负债表={len(balance)}期, 利润表={len(income)}期, "
              f"现金流量表={len(cashflow)}期, 财务指标={len(fina)}期")
    
    print("\n✓ 阶段2完成：数据库写入验证通过")
    
    # ========================================================================
    # 阶段3: 计算核心指标
    # ========================================================================
    print("\n【阶段3】计算核心指标")
    print("-"*80)
    
    analyzer = CoreIndicatorsAnalyzer()
    
    for ts_code in test_stocks:
        print(f"\n3.1 计算 {ts_code} 的核心指标...")
        
        # 获取财务数据
        balance = db.get_financial_data(ts_code, 'balancesheet')
        income = db.get_financial_data(ts_code, 'income')
        cashflow = db.get_financial_data(ts_code, 'cashflow')
        
        # 计算指标
        indicators = analyzer.calculate_all_indicators(balance, income, cashflow)
        
        if len(indicators) == 0:
            print(f"  ✗ {ts_code}: 指标计算失败")
            return False
        
        print(f"  ✓ {ts_code}: 成功计算 {len(indicators)} 期指标")
        
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
        
        print(f"  ✓ {ts_code}: 已保存 {saved_count} 期指标到数据库")
    
    print("\n✓ 阶段3完成：核心指标计算并保存")
    
    # ========================================================================
    # 阶段4: 计算市场分位数
    # ========================================================================
    print("\n【阶段4】计算市场分位数")
    print("-"*80)
    
    market_analyzer = MarketAnalyzer(db)
    
    # 分析所有报告期
    print("\n4.1 分析所有报告期...")
    results = market_analyzer.analyze_all_periods(exclude_outliers=True)
    
    if len(results) == 0:
        print("  ✗ 市场分析失败")
        return False
    
    print(f"  ✓ 成功分析 {len(results)} 个报告期")
    
    # 显示最新报告期的市场分布
    latest_period = list(results.keys())[-1]
    market_stats = market_analyzer.calculate_market_percentiles(latest_period)
    
    print(f"\n4.2 最新报告期 ({latest_period}) 市场分布:")
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
    
    print("\n✓ 阶段4完成：市场分位数计算完成")
    
    # ========================================================================
    # 阶段5: 验证分位数排名
    # ========================================================================
    print("\n【阶段5】验证分位数排名")
    print("-"*80)
    
    for ts_code in test_stocks:
        history = market_analyzer.get_stock_percentile_history(ts_code)
        
        if len(history) == 0:
            print(f"  ✗ {ts_code}: 未找到分位数数据")
            return False
        
        # 显示最新一期的排名
        latest = history.iloc[-1]
        print(f"\n  {ts_code} 最新排名 ({int(latest['end_date'])}):")
        print(f"    应收账款周转率对数: {latest['ar_turnover_log_percentile']:.1f}%" if pd.notna(latest['ar_turnover_log_percentile']) else "    应收账款周转率对数: N/A")
        print(f"    毛利率: {latest['gross_margin_percentile']:.1f}%" if pd.notna(latest['gross_margin_percentile']) else "    毛利率: N/A")
        print(f"    长期经营资产周转率对数: {latest['lta_turnover_log_percentile']:.1f}%" if pd.notna(latest['lta_turnover_log_percentile']) else "    长期经营资产周转率对数: N/A")
        print(f"    净营运资本比率: {latest['working_capital_ratio_percentile']:.1f}%" if pd.notna(latest['working_capital_ratio_percentile']) else "    净营运资本比率: N/A")
        print(f"    经营现金流比率: {latest['ocf_ratio_percentile']:.1f}%" if pd.notna(latest['ocf_ratio_percentile']) else "    经营现金流比率: N/A")
    
    print("\n✓ 阶段5完成：分位数排名验证通过")
    
    # ========================================================================
    # 最终验证
    # ========================================================================
    print("\n" + "="*80)
    print("【最终验证】完整流程测试")
    print("="*80)
    
    print("\n✅ 所有阶段测试通过！")
    print("\n测试覆盖:")
    print("  ✓ Tushare API数据获取")
    print("  ✓ 数据库写入（4张报表）")
    print("  ✓ 核心指标计算（4大指标）")
    print("  ✓ 市场分位数计算")
    print("  ✓ 分位数排名更新")
    print("  ✓ 历史数据查询")
    
    print("\n系统已准备就绪，可以开始全A股数据获取！")
    print("="*80)
    
    return True


if __name__ == '__main__':
    import pandas as pd
    test_full_pipeline()
