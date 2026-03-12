"""
测试字段翻译功能
"""

from tushare_client import TushareClient
import pandas as pd


def test_translation():
    """测试字段翻译功能"""
    print("="*60)
    print("字段翻译功能测试")
    print("="*60)
    
    # 初始化客户端
    client = TushareClient(config_path='config.yaml')
    
    # 测试股票
    ts_code = '000001.SZ'
    
    print(f"\n测试 {ts_code} 的字段翻译功能...")
    
    # 1. 获取财务指标表（原始英文）
    print("\n1. 获取财务指标表（原始英文字段）:")
    print("-" * 60)
    df_en = client.get_fina_indicator(ts_code, start_date='20230101', end_date='20231231', translate=False)
    if df_en is not None and len(df_en) > 0:
        print(f"前10个字段: {list(df_en.columns[:10])}")
    
    # 2. 获取财务指标表（翻译为中文）
    print("\n2. 获取财务指标表（翻译为中文字段）:")
    print("-" * 60)
    df_cn = client.get_fina_indicator(ts_code, start_date='20230101', end_date='20231231', translate=True)
    if df_cn is not None and len(df_cn) > 0:
        print(f"前10个字段: {list(df_cn.columns[:10])}")
    
    # 3. 资产负债表翻译
    print("\n3. 资产负债表字段翻译:")
    print("-" * 60)
    df_balance = client.get_balancesheet(ts_code, start_date='20230101', end_date='20231231', translate=True)
    if df_balance is not None and len(df_balance) > 0:
        print(f"前10个字段: {list(df_balance.columns[:10])}")
    
    # 4. 利润表翻译
    print("\n4. 利润表字段翻译:")
    print("-" * 60)
    df_income = client.get_income(ts_code, start_date='20230101', end_date='20231231', translate=True)
    if df_income is not None and len(df_income) > 0:
        print(f"前10个字段: {list(df_income.columns[:10])}")
    
    # 5. 现金流量表翻译
    print("\n5. 现金流量表字段翻译:")
    print("-" * 60)
    df_cashflow = client.get_cashflow(ts_code, start_date='20230101', end_date='20231231', translate=True)
    if df_cashflow is not None and len(df_cashflow) > 0:
        print(f"前10个字段: {list(df_cashflow.columns[:10])}")
    
    # 6. 显示翻译后的数据样例
    print("\n6. 翻译后的财务指标数据样例:")
    print("="*60)
    if df_cn is not None and len(df_cn) > 0:
        # 显示部分关键数据
        display_cols = ['TS代码', '报告期', '基本每股收益', '净资产收益率', '销售毛利率']
        available_cols = [col for col in display_cols if col in df_cn.columns]
        if available_cols:
            print(df_cn[available_cols].head(3).to_string(index=False))
        else:
            print(df_cn.head(3).to_string(index=False))
    
    print("\n" + "="*60)
    print("✓ 字段翻译功能测试完成！")
    print("="*60)
    
    return {
        'fina_indicator': df_cn,
        'balancesheet': df_balance,
        'income': df_income,
        'cashflow': df_cashflow
    }


if __name__ == '__main__':
    test_translation()
