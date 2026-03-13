"""
主程序：从 Tushare 获取公司财务数据
"""

import argparse
from datetime import datetime
from tushare_client import TushareClient
from balance_sheet_restructure import restructure_balance_sheet
from income_statement_restructure import restructure_income_statement
from cashflow_statement_restructure import restructure_cashflow_statement
from annual_report_generator import AnnualReportGenerator
import os
import yaml


def normalize_stock_code(ts_code: str) -> str:
    """
    规范化股票代码，自动补全交易所后缀
    
    Args:
        ts_code: 股票代码（可以是纯数字或带后缀）
        
    Returns:
        规范化后的股票代码（带交易所后缀）
    
    Examples:
        '000333' -> '000333.SZ'
        '600519' -> '600519.SH'
        '000001.SZ' -> '000001.SZ'
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


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='从 Tushare 获取公司财务数据')
    parser.add_argument('ts_code', type=str, help='股票代码（例如：000333 或 600519.SH）')
    parser.add_argument('--start-date', type=str, help='开始日期（YYYYMMDD）')
    parser.add_argument('--end-date', type=str, help='结束日期（YYYYMMDD）')
    parser.add_argument('--output-dir', type=str, default='./data', help='数据输出目录')
    parser.add_argument('--format', type=str, choices=['csv', 'excel', 'both'], 
                       default='csv', help='输出格式（csv/excel/both）')
    parser.add_argument('--no-transpose', action='store_true', 
                       help='不转置数据（使用原始格式：字段横向，时间纵向）')
    parser.add_argument('--no-translate', action='store_true', help='不翻译字段名（使用英文列名）')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    parser.add_argument('--annual-ttm', action='store_true', 
                       help='生成年报+TTM重构报表（过去10年年报+最新一期TTM）')
    parser.add_argument('--years', type=int, default=10, 
                       help='年报年数（默认10年，仅当--annual-ttm时有效）')
    
    args = parser.parse_args()
    
    # 规范化股票代码（自动补全交易所后缀）
    ts_code = normalize_stock_code(args.ts_code)
    
    # 初始化客户端
    print(f"初始化 Tushare 客户端...")
    client = TushareClient(config_path=args.config)
    
    # 获取财务数据
    print(f"\n开始获取 {ts_code} 的财务数据...")
    if args.start_date:
        print(f"日期范围: {args.start_date} 至 {args.end_date or '至今'}")
    else:
        print(f"获取全部历史数据...")
    
    # 默认翻译为中文
    translate = not args.no_translate
    if translate:
        print(f"字段名翻译: 中文（默认）")
    else:
        print(f"字段名翻译: 英文")
    
    # 默认转置数据格式
    transpose = not args.no_transpose
    if transpose:
        print(f"数据格式: 转置（字段纵向，时间横向）- 便于分析")
    else:
        print(f"数据格式: 原始（字段横向，时间纵向）")
    
    data = client.get_all_financial_data(
        ts_code=ts_code,
        start_date=args.start_date,
        end_date=args.end_date,
        translate=translate
    )
    
    # 保存数据
    print(f"\n保存数据到: {args.output_dir}")
    if args.format in ['csv', 'both']:
        client.save_to_csv(data, ts_code, args.output_dir, transpose=transpose)
    
    if args.format in ['excel', 'both']:
        client.save_to_excel(data, ts_code, args.output_dir, transpose=transpose)
    
    # 重构资产负债表
    if data.get('balancesheet') is not None and len(data['balancesheet']) > 0:
        print(f"\n重构资产负债表...")
        try:
            # 获取原始资产负债表数据并转置
            df_balance = data['balancesheet'].copy()
            df_transposed = client.transpose_data(df_balance)
            
            # 重构资产负债表
            df_restructured = restructure_balance_sheet(df_transposed)
            
            # 保存重构后的数据
            restructured_filename = os.path.join(args.output_dir, f"{ts_code}_balancesheet_restructured.csv")
            df_restructured.to_csv(restructured_filename, index=False, encoding='utf-8-sig')
            print(f"✓ 重构后的资产负债表已保存到: {restructured_filename}")
            
            # 添加到data字典
            data['balancesheet_restructured'] = df_restructured
            
            # 如果需要Excel格式，也保存Excel
            if args.format in ['excel', 'both']:
                excel_filename = os.path.join(args.output_dir, f"{ts_code}_balancesheet_restructured.xlsx")
                df_restructured.to_excel(excel_filename, index=False)
                print(f"✓ Excel格式已保存到: {excel_filename}")
        except Exception as e:
            print(f"⚠️  资产负债表重构失败: {e}")
    
    # 重构利润表
    if data.get('income') is not None and len(data['income']) > 0:
        print(f"\n重构利润表（股权价值增加表）...")
        try:
            # 读取配置文件获取股权资本成本率
            equity_cost_rate = 0.08  # 默认值
            try:
                with open(args.config, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and 'restructure' in config:
                        equity_cost_rate = config['restructure'].get('equity_cost_rate', 0.08)
            except Exception as e:
                print(f"  使用默认股权资本成本率: {equity_cost_rate*100}%")
            
            print(f"  股权资本成本率: {equity_cost_rate*100}%")
            
            # 获取原始利润表数据并转置
            df_income = data['income'].copy()
            df_transposed = client.transpose_data(df_income)
            
            # 获取资产负债表重构数据（用于获取所有者权益合计）
            balance_restructured = data.get('balancesheet_restructured')
            
            # 重构利润表
            df_restructured = restructure_income_statement(
                df_transposed, 
                equity_data=balance_restructured,
                equity_cost_rate=equity_cost_rate
            )
            
            # 保存重构后的数据
            restructured_filename = os.path.join(args.output_dir, f"{ts_code}_income_restructured.csv")
            df_restructured.to_csv(restructured_filename, index=False, encoding='utf-8-sig')
            print(f"✓ 重构后的利润表已保存到: {restructured_filename}")
            
            # 添加到data字典
            data['income_restructured'] = df_restructured
            
            # 如果需要Excel格式，也保存Excel
            if args.format in ['excel', 'both']:
                excel_filename = os.path.join(args.output_dir, f"{ts_code}_income_restructured.xlsx")
                df_restructured.to_excel(excel_filename, index=False)
                print(f"✓ Excel格式已保存到: {excel_filename}")
        except Exception as e:
            print(f"⚠️  利润表重构失败: {e}")
    
    # 重构现金流量表
    if data.get('cashflow') is not None and len(data['cashflow']) > 0:
        print(f"\n重构现金流量表...")
        try:
            # 获取原始现金流量表数据并转置
            df_cashflow = data['cashflow'].copy()
            df_transposed = client.transpose_data(df_cashflow)
            
            # 获取利润表原始数据并转置(用于营业收入、营业总成本)
            income_original = None
            if data.get('income') is not None:
                income_original = client.transpose_data(data['income'].copy())
            
            # 获取资产负债表重构数据(用于长期经营资产合计)
            balance_restructured = data.get('balancesheet_restructured')
            
            # 获取利润表重构数据(用于息前税后经营利润、净利润)
            income_restructured = data.get('income_restructured')
            
            # 重构现金流量表
            df_restructured = restructure_cashflow_statement(
                df_transposed,
                income_data=income_original,
                balance_data=balance_restructured,
                income_restructured=income_restructured
            )
            
            # 保存重构后的数据
            restructured_filename = os.path.join(args.output_dir, f"{ts_code}_cashflow_restructured.csv")
            df_restructured.to_csv(restructured_filename, index=False, encoding='utf-8-sig')
            print(f"✓ 重构后的现金流量表已保存到: {restructured_filename}")
            
            # 添加到data字典
            data['cashflow_restructured'] = df_restructured
            
            # 如果需要Excel格式,也保存Excel
            if args.format in ['excel', 'both']:
                excel_filename = os.path.join(args.output_dir, f"{ts_code}_cashflow_restructured.xlsx")
                df_restructured.to_excel(excel_filename, index=False)
                print(f"✓ Excel格式已保存到: {excel_filename}")
        except Exception as e:
            print(f"⚠️  现金流量表重构失败: {e}")
    
    # 生成年报+TTM重构报表
    if args.annual_ttm:
        print(f"\n" + "="*60)
        print("生成年报+TTM重构报表...")
        print("="*60)
        
        try:
            # 获取重构后的数据
            balance_restructured = data.get('balancesheet_restructured')
            income_restructured = data.get('income_restructured')
            cashflow_restructured = data.get('cashflow_restructured')
            
            if balance_restructured is not None and income_restructured is not None and cashflow_restructured is not None:
                # 初始化生成器
                annual_generator = AnnualReportGenerator()
                
                # 生成年报+TTM数据
                annual_reports = annual_generator.generate_annual_reports_with_ttm(
                    balance_restructured, income_restructured, cashflow_restructured, 
                    years=args.years
                )
                
                # 保存年报+TTM报表
                for report_name, df_report in annual_reports.items():
                    if df_report is not None and len(df_report) > 0:
                        # 格式化
                        df_formatted = annual_generator.format_annual_report(df_report, report_name)
                        
                        # 保存CSV
                        csv_filename = os.path.join(args.output_dir, f"{ts_code}_{report_name}_annual_ttm.csv")
                        df_formatted.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                        print(f"✓ {report_name}年报+TTM已保存到: {csv_filename}")
                        
                        # 添加到data字典
                        data[f'{report_name}_annual_ttm'] = df_formatted
                        
                        # 如果需要Excel格式，也保存Excel
                        if args.format in ['excel', 'both']:
                            excel_filename = os.path.join(args.output_dir, f"{ts_code}_{report_name}_annual_ttm.xlsx")
                            df_formatted.to_excel(excel_filename, index=False)
                            print(f"✓ Excel格式已保存到: {excel_filename}")
            else:
                print("⚠️  缺少重构数据，无法生成年报+TTM报表")
        except Exception as e:
            print(f"⚠️  生成年报+TTM报表失败: {e}")
    
    # 显示数据摘要
    print("\n" + "="*60)
    print("数据摘要:")
    print("="*60)
    for name, df in data.items():
        if df is not None and len(df) > 0:
            print(f"{name:30s}: {len(df):6d} 条记录, {len(df.columns)} 个字段")
            
            # 特殊处理重构后的资产负债表
            if name == 'balancesheet_restructured':
                # 重构后的数据第一列是"项目"，其余列是日期
                if '项目' in df.columns:
                    print(f"  报告期数: {len(df.columns) - 1} 期")
                    print(f"  项目数: {len(df)}")
                continue
            
            # 特殊处理重构后的利润表
            if name == 'income_restructured':
                # 重构后的数据第一列是"项目",其余列是日期
                if '项目' in df.columns:
                    print(f"  报告期数: {len(df.columns) - 1} 期")
                    print(f"  项目数: {len(df)}")
                continue
            
            # 特殊处理重构后的现金流量表
            if name == 'cashflow_restructured':
                # 重构后的数据第一列是"项目",其余列是日期
                if '项目' in df.columns:
                    print(f"  报告期数: {len(df.columns) - 1} 期")
                    print(f"  项目数: {len(df)}")
                continue
            
            # 根据是否翻译选择列名
            date_col = '报告期' if '报告期' in df.columns else 'end_date'
            if date_col in df.columns:
                print(f"  日期范围: {df[date_col].min()} 至 {df[date_col].max()}")
        else:
            print(f"{name:30s}: 无数据")
    print("="*60)
    
    print(f"\n完成！数据已保存到 {args.output_dir}")


if __name__ == '__main__':
    main()
