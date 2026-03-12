"""
使用示例：展示如何使用 TushareClient 获取财务数据
"""

from tushare_client import TushareClient
import pandas as pd


def example_basic_usage():
    """基础使用示例：获取单家公司的全部财务数据"""
    print("="*60)
    print("示例 1: 获取平安银行(000001.SZ)的全部历史财务数据")
    print("="*60)
    
    # 初始化客户端
    client = TushareClient(config_path='config.yaml')
    
    # 获取全部财务数据
    ts_code = '000001.SZ'
    data = client.get_all_financial_data(ts_code)
    
    # 保存为 CSV
    client.save_to_csv(data, ts_code, output_dir='./data')
    
    # 显示数据概览
    print("\n财务指标表预览（前5行）:")
    print(data['fina_indicator'].head())
    
    print("\n资产负债表预览（前5行）:")
    print(data['balancesheet'].head())
    
    return data


def example_date_range():
    """指定日期范围示例"""
    print("\n" + "="*60)
    print("示例 2: 获取贵州茅台(600519.SH)最近3年的财务数据")
    print("="*60)
    
    client = TushareClient(config_path='config.yaml')
    
    # 获取最近3年的数据
    ts_code = '600519.SH'
    data = client.get_all_financial_data(
        ts_code=ts_code,
        start_date='20210101',  # 2021年1月1日开始
        end_date='20231231'     # 2023年12月31日结束
    )
    
    # 保存为 Excel
    client.save_to_excel(data, ts_code, output_dir='./data')
    
    return data


def example_single_report():
    """获取单个报表示例"""
    print("\n" + "="*60)
    print("示例 3: 只获取利润表数据")
    print("="*60)
    
    client = TushareClient(config_path='config.yaml')
    
    ts_code = '000858.SZ'  # 五粮液
    income_df = client.get_income(ts_code)
    
    if income_df is not None:
        print(f"\n获取到 {len(income_df)} 条利润表数据")
        
        # 简单分析：营业收入趋势
        print("\n营业收入趋势（最近5期）:")
        recent_data = income_df.nlargest(5, 'end_date')[['end_date', 'revenue', 'total_revenue', 'n_income']]
        print(recent_data.to_string(index=False))
    
    return income_df


def example_custom_analysis():
    """自定义分析示例"""
    print("\n" + "="*60)
    print("示例 4: 财务指标分析")
    print("="*60)
    
    client = TushareClient(config_path='config.yaml')
    
    # 获取财务指标
    ts_code = '000333.SZ'  # 美的集团
    fina_indicator = client.get_fina_indicator(ts_code)
    
    if fina_indicator is not None:
        print(f"\n获取到 {len(fina_indicator)} 条财务指标数据")
        
        # 分析 ROE 趋势
        print("\nROE（净资产收益率）趋势（最近5期）:")
        recent_data = fina_indicator.nlargest(5, 'end_date')[['end_date', 'roe', 'roa', 'netprofit_margin']]
        print(recent_data.to_string(index=False))
        
        # 分析成长能力
        print("\n成长能力指标（最近5期）:")
        growth_cols = ['end_date', 'or_yoy', 'netprofit_yoy', 'op_yoy']
        recent_growth = fina_indicator.nlargest(5, 'end_date')[growth_cols]
        print(recent_growth.to_string(index=False))
    
    return fina_indicator


def example_multiple_stocks():
    """批量获取多只股票示例"""
    print("\n" + "="*60)
    print("示例 5: 批量获取多只股票的财务数据")
    print("="*60)
    
    client = TushareClient(config_path='config.yaml')
    
    # 定义股票列表
    stocks = [
        ('000001.SZ', '平安银行'),
        ('600519.SH', '贵州茅台'),
        ('000858.SZ', '五粮液'),
    ]
    
    all_data = {}
    
    for ts_code, name in stocks:
        print(f"\n正在获取 {name}({ts_code}) 的数据...")
        data = client.get_all_financial_data(ts_code)
        all_data[ts_code] = data
        
        # 保存数据
        client.save_to_csv(data, ts_code, output_dir='./data/batch')
    
    print(f"\n批量获取完成！共 {len(all_data)} 家公司")
    
    return all_data


def example_filter_data():
    """数据过滤示例"""
    print("\n" + "="*60)
    print("示例 6: 过滤特定报告类型的数据")
    print("="*60)
    
    client = TushareClient(config_path='config.yaml')
    
    ts_code = '000001.SZ'
    balance_df = client.get_balancesheet(ts_code)
    
    if balance_df is not None:
        # 只看合并报表（report_type='1'）
        consolidated = balance_df[balance_df['report_type'] == '1']
        print(f"\n合并资产负债表: {len(consolidated)} 条记录")
        
        # 只看年报（end_type='4' 代表年报）
        annual_reports = balance_df[balance_df['end_type'] == '4']
        print(f"年度报告: {len(annual_reports)} 条记录")
        
        # 查看最近的年报数据
        print("\n最近3年资产负债表关键指标:")
        recent = annual_reports.nlargest(3, 'end_date')[
            ['end_date', 'total_assets', 'total_liab', 'total_hldr_eqy_inc_min_int']
        ]
        print(recent.to_string(index=False))
    
    return balance_df


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Tushare 财务数据获取工具 - 使用示例")
    print("="*60)
    
    # 运行各个示例
    print("\n请选择要运行的示例：")
    print("1. 获取单家公司的全部财务数据")
    print("2. 获取指定日期范围的财务数据")
    print("3. 只获取利润表数据")
    print("4. 财务指标分析")
    print("5. 批量获取多只股票")
    print("6. 数据过滤示例")
    print("0. 运行所有示例")
    
    choice = input("\n请输入选择 (0-6): ").strip()
    
    if choice == '0':
        # 运行所有示例
        example_basic_usage()
        example_date_range()
        example_single_report()
        example_custom_analysis()
        example_multiple_stocks()
        example_filter_data()
    elif choice == '1':
        example_basic_usage()
    elif choice == '2':
        example_date_range()
    elif choice == '3':
        example_single_report()
    elif choice == '4':
        example_custom_analysis()
    elif choice == '5':
        example_multiple_stocks()
    elif choice == '6':
        example_filter_data()
    else:
        print("无效的选择！")
    
    print("\n示例运行完成！")
