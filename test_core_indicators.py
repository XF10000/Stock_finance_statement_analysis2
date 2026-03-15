"""
测试核心指标分析器
"""

import logging
from market_data_manager import MarketDataManager
from core_indicators_analyzer import CoreIndicatorsAnalyzer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_single_stock():
    """测试单只股票的指标计算"""
    
    print("="*80)
    print("测试核心指标分析器")
    print("="*80)
    
    # 初始化
    db = MarketDataManager('database/market_data_test.db')
    analyzer = CoreIndicatorsAnalyzer()
    
    # 测试股票
    test_stocks = [
        ('600519.SH', '贵州茅台'),
        ('000333.SZ', '美的集团'),
        ('000858.SZ', '五粮液')
    ]
    
    for ts_code, name in test_stocks:
        print(f"\n{'='*80}")
        print(f"测试 {ts_code} - {name}")
        print('='*80)
        
        # 获取财务数据
        print("\n1. 获取财务数据...")
        balance = db.get_financial_data(ts_code, 'balancesheet')
        income = db.get_financial_data(ts_code, 'income')
        cashflow = db.get_financial_data(ts_code, 'cashflow')
        
        if balance is None or income is None or cashflow is None:
            print(f"  ✗ 数据获取失败")
            continue
        
        print(f"  ✓ 资产负债表: {len(balance)} 条")
        print(f"  ✓ 利润表: {len(income)} 条")
        print(f"  ✓ 现金流量表: {len(cashflow)} 条")
        
        # 计算指标
        print("\n2. 计算核心指标...")
        try:
            indicators = analyzer.calculate_all_indicators(
                balance, income, cashflow
            )
            
            if len(indicators) == 0:
                print(f"  ✗ 未能计算出指标")
                continue
            
            print(f"  ✓ 成功计算 {len(indicators)} 期指标")
            
            # 显示最近5期的指标
            print("\n3. 最近5期指标:")
            print("-"*80)
            
            recent = indicators.tail(5)
            
            # 显示列名
            cols_to_show = [
                '报告期',
                '应收账款周转率对数',
                '毛利率',
                '长期经营资产周转率对数',
                '净营运资本比率',
                '经营现金流比率'
            ]
            
            print(f"\n{'报告期':>10}", end='')
            for col in cols_to_show[1:]:
                print(f"{col:>15}", end='')
            print()
            print("-"*80)
            
            for _, row in recent.iterrows():
                print(f"{row['报告期']:>10}", end='')
                for col in cols_to_show[1:]:
                    value = row[col]
                    if pd.notna(value):
                        print(f"{value:>15.2f}", end='')
                    else:
                        print(f"{'N/A':>15}", end='')
                print()
            
            # 保存到数据库
            print("\n4. 保存指标到数据库...")
            saved_count = 0
            for _, row in indicators.iterrows():
                # 构建指标字典
                indicator_dict = {
                    'ar_turnover_log': row.get('应收账款周转率对数'),
                    'gross_margin': row.get('毛利率'),
                    'lta_turnover_log': row.get('长期经营资产周转率对数'),
                    'working_capital_ratio': row.get('净营运资本比率'),
                    'ocf_ratio': row.get('经营现金流比率')
                }
                
                # 保存
                db.save_core_indicators(
                    ts_code=ts_code,
                    end_date=str(int(row['报告期'])),
                    indicators=indicator_dict
                )
                saved_count += 1
            
            print(f"  ✓ 已保存 {saved_count} 期指标")
            
        except Exception as e:
            print(f"  ✗ 计算失败: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == '__main__':
    import pandas as pd
    test_single_stock()
