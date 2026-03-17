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
import pandas as pd
import time


def get_total_share_data(client: TushareClient, ts_code: str, balance_df: pd.DataFrame) -> dict:
    """
    获取总股本数据
    
    Args:
        client: TushareClient实例
        ts_code: 股票代码
        balance_df: 资产负债表数据
        
    Returns:
        字典，key为报告期（YYYYMMDD格式），value为总股本（股）
    """
    if balance_df is None or len(balance_df) == 0:
        return None
    
    # 获取所有报告期
    end_date_col = '报告期' if '报告期' in balance_df.columns else 'end_date'
    if end_date_col not in balance_df.columns:
        return None
    
    report_dates = balance_df[end_date_col].unique()
    total_share_dict = {}
    
    for report_date in report_dates:
        try:
            # 提取年份
            year = str(report_date)[:4]
            
            # 查询该年度12月的交易日数据
            start_date = f"{year}1201"
            end_date = f"{year}1231"
            
            df = client.pro.daily_basic(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields='trade_date,total_share'
            )
            
            if df is not None and len(df) > 0:
                # 取最后一个交易日的总股本
                df = df.sort_values('trade_date', ascending=False)
                total_share = df['total_share'].values[0] * 10000 if pd.notna(df['total_share'].values[0]) else None
                total_share_dict[str(report_date)] = total_share
            
            # API限流
            time.sleep(0.3)
        except Exception as e:
            print(f"  获取 {report_date} 总股本失败: {e}")
            continue
    
    return total_share_dict if total_share_dict else None


def add_total_share_to_balance(df_balance: pd.DataFrame, total_share_data: dict) -> pd.DataFrame:
    """
    将总股本数据添加到资产负债表中
    
    Args:
        df_balance: 重构后的资产负债表
        total_share_data: 总股本数据字典
        
    Returns:
        添加了总股本行的资产负债表
    """
    # 创建总股本行
    total_share_row = {'项目': '总股本'}
    
    # 获取所有日期列
    date_columns = [col for col in df_balance.columns if col != '项目']
    
    for col in date_columns:
        # 将列名转换为YYYYMMDD格式
        col_key = col.replace('/', '').replace('-', '').replace('Q3-TTM', '')
        if 'TTM' in col:
            col_key = col[:4] + '1231'  # TTM使用当年12月31日
        
        total_share_row[col] = total_share_data.get(col_key)
    
    # 将总股本行添加到资产负债表末尾
    df_result = pd.concat([df_balance, pd.DataFrame([total_share_row])], ignore_index=True)
    
    return df_result


def get_dividend_data(client: TushareClient, ts_code: str, output_dir: str) -> pd.DataFrame:
    """
    获取分红送股数据并保存为Excel文件
    
    Args:
        client: TushareClient实例
        ts_code: 股票代码
        output_dir: 输出目录
        
    Returns:
        分红送股数据DataFrame
    """
    try:
        # 获取分红数据
        df = client.pro.dividend(
            ts_code=ts_code,
            fields='end_date,ann_date,div_proc,stk_div,stk_bo_rate,stk_co_rate,cash_div,cash_div_tax,record_date,ex_date,pay_date,div_listdate,imp_ann_date'
        )
        
        if df is None or len(df) == 0:
            print("  未获取到分红数据")
            return None
        
        # 按报告期排序
        df = df.sort_values('end_date', ascending=False)
        
        # 重命名列为中文
        df_renamed = df.rename(columns={
            'end_date': '报告期',
            'ann_date': '公告日期',
            'div_proc': '分红进度',
            'stk_div': '送股比例',
            'stk_bo_rate': '转增比例',
            'stk_co_rate': '配股比例',
            'cash_div': '每股派息(税前)',
            'cash_div_tax': '每股派息(税后)',
            'record_date': '股权登记日',
            'ex_date': '除权除息日',
            'pay_date': '派息日',
            'div_listdate': '红股上市日',
            'imp_ann_date': '实施公告日'
        })
        
        # 保存为Excel
        excel_filename = os.path.join(output_dir, f"{ts_code}_分红送股.xlsx")
        df_renamed.to_excel(excel_filename, index=False)
        print(f"✓ 分红送股数据已保存到: {excel_filename}")
        
        return df_renamed
    except Exception as e:
        print(f"  获取分红数据失败: {e}")
        return None


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
    parser.add_argument('--annual-ttm', action='store_true', default=True,
                       help='生成年报+TTM重构报表（默认开启，使用--no-annual-ttm关闭）')
    parser.add_argument('--no-annual-ttm', action='store_true',
                       help='不生成年报+TTM数据')
    parser.add_argument('--years', type=int, default=None, 
                       help='年报年数（默认覆盖所有历史数据）')
    
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
    
    # 获取总股本数据
    print(f"\n获取总股本数据...")
    total_share_data = None
    try:
        total_share_data = get_total_share_data(client, ts_code, data.get('balancesheet'))
        if total_share_data:
            print(f"✓ 成功获取 {len(total_share_data)} 个报告期的总股本数据")
    except Exception as e:
        print(f"⚠️  获取总股本数据失败: {e}")
    
    # 获取分红数据
    print(f"\n获取分红送股数据...")
    try:
        dividend_df = get_dividend_data(client, ts_code, args.output_dir)
        if dividend_df is not None:
            print(f"✓ 成功获取分红送股数据，共 {len(dividend_df)} 条记录")
            data['dividend'] = dividend_df
    except Exception as e:
        print(f"⚠️  获取分红送股数据失败: {e}")
    
    # 重构资产负债表
    if data.get('balancesheet') is not None and len(data['balancesheet']) > 0:
        print(f"\n重构资产负债表...")
        try:
            # 获取原始资产负债表数据并转置
            df_balance = data['balancesheet'].copy()
            df_transposed = client.transpose_data(df_balance)
            
            # 重构资产负债表
            df_restructured = restructure_balance_sheet(df_transposed)
            
            # 将总股本数据添加到重构的资产负债表中
            if total_share_data:
                df_restructured = add_total_share_to_balance(df_restructured, total_share_data)
                print(f"✓ 总股本数据已添加到资产负债表")
            
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
    
    # 生成年报+TTM重构报表（默认开启，除非使用--no-annual-ttm）
    if args.annual_ttm and not args.no_annual_ttm:
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
                
                # 如果years为None，计算覆盖所有历史数据的年数
                years = args.years
                if years is None:
                    # 获取所有日期列
                    date_cols = [col for col in balance_restructured.columns if col != '项目']
                    if date_cols:
                        # 找到最早和最新的年份
                        years_list = [int(col[:4]) for col in date_cols if len(col) >= 4 and col[:4].isdigit()]
                        if years_list:
                            min_year = min(years_list)
                            max_year = max(years_list)
                            years = max_year - min_year + 1
                            print(f"覆盖所有历史数据：{min_year}年至{max_year}年，共{years}年")
                        else:
                            years = 10  # 默认10年
                    else:
                        years = 10  # 默认10年
                
                # 生成年报+TTM数据
                annual_reports = annual_generator.generate_annual_reports_with_ttm(
                    balance_restructured, income_restructured, cashflow_restructured, 
                    years=years
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
    
    # 自动生成HTML报告
    if args.annual_ttm and not args.no_annual_ttm:
        print("\n" + "="*60)
        print("生成HTML财务分析报告...")
        print("="*60)
        
        try:
            from html_report_generator import HTMLReportGenerator
            
            # 检查是否有年报+TTM数据
            balance_ttm = data.get('balance_sheet_annual_ttm')
            income_ttm = data.get('income_statement_annual_ttm')
            cashflow_ttm = data.get('cashflow_statement_annual_ttm')
            
            if balance_ttm is not None and income_ttm is not None and cashflow_ttm is not None:
                # 获取公司名称（从股票代码推断，或使用默认值）
                company_name_map = {
                    '000333.SZ': '美的集团',
                    '600900.SH': '长江电力',
                    '603345.SH': '安井食品',
                    '601898.SH': '中煤能源',
                    '601088.SH': '中国神华'
                }
                company_name = company_name_map.get(ts_code, ts_code.split('.')[0])
                
                # 生成HTML报告
                html_filename = os.path.join(args.output_dir, f"{ts_code}_financial_report.html")
                generator = HTMLReportGenerator(company_name=company_name, stock_code=ts_code)
                generator.generate_report(
                    balance_ttm, income_ttm, cashflow_ttm,
                    output_path=html_filename
                )
                
                print(f"\n提示: 在浏览器中打开该文件即可查看交互式财务分析报告")
            else:
                print("⚠️  缺少年报+TTM数据，无法生成HTML报告")
        except Exception as e:
            print(f"⚠️  生成HTML报告失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 计算并保存核心指标到数据库（仅更新新季度）
    print("\n" + "="*60)
    print("检查并更新核心指标...")
    print("="*60)
    
    try:
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        from financial_data_manager import FinancialDataManager
        
        # 初始化数据库管理器
        db_manager = FinancialDataManager('database/financial_data.db')
        analyzer = CoreIndicatorsAnalyzer()
        
        # 获取三大报表数据
        balance_data = data.get('balancesheet')
        income_data = data.get('income')
        cashflow_data = data.get('cashflow')
        
        if balance_data is not None and income_data is not None and cashflow_data is not None:
            # 获取数据库中已有的核心指标季度
            conn = db_manager.get_connection()
            existing_quarters_query = '''
                SELECT DISTINCT end_date 
                FROM core_indicators 
                WHERE ts_code = ? AND ar_turnover_log IS NOT NULL
            '''
            existing_df = pd.read_sql_query(existing_quarters_query, conn, params=(ts_code,))
            existing_quarters = set(existing_df['end_date'].tolist()) if len(existing_df) > 0 else set()
            
            # 计算所有核心指标
            indicators_df = analyzer.calculate_all_indicators(balance_data, income_data, cashflow_data)
            
            if len(indicators_df) > 0:
                # 筛选出需要更新的季度（数据库中不存在或为空的）
                date_col = 'end_date' if 'end_date' in indicators_df.columns else '报告期'
                new_quarters = []
                
                for _, row in indicators_df.iterrows():
                    end_date = row.get('end_date') or row.get('报告期')
                    if isinstance(end_date, str):
                        end_date = end_date.replace('-', '')
                    
                    # 只保存数据库中不存在的季度
                    if str(end_date) not in existing_quarters:
                        new_quarters.append(end_date)
                        
                        indicators_dict = {
                            'ar_turnover_log': row.get('ar_turnover_log') or row.get('应收账款周转率对数'),
                            'gross_margin': row.get('gross_margin') or row.get('毛利率'),
                            'lta_turnover_log': row.get('lta_turnover_log') or row.get('长期经营资产周转率对数'),
                            'working_capital_ratio': row.get('working_capital_ratio') or row.get('净营运资本比率'),
                            'ocf_ratio': row.get('ocf_ratio') or row.get('经营现金流比率'),
                        }
                        
                        db_manager.save_core_indicators(
                            ts_code=ts_code,
                            end_date=str(end_date),
                            indicators=indicators_dict,
                            data_complete=1
                        )
                
                if len(new_quarters) > 0:
                    print(f"✓ 新增 {len(new_quarters)} 个季度的核心指标")
                    print(f"  跳过已有 {len(existing_quarters)} 个季度")
                    
                    # 只更新新季度的分位数排名
                    print("\n更新新季度的分位数排名...")
                    try:
                        from financial_data_analyzer import FinancialDataAnalyzer
                        
                        analyzer_market = FinancialDataAnalyzer(db_manager)
                        
                        total_updated = 0
                        for end_date in new_quarters:
                            # 转换日期格式
                            if isinstance(end_date, str):
                                end_date = end_date.replace('-', '')
                            
                            # 只更新该季度的分位数（只影响该季度的所有股票）
                            count = analyzer_market.update_percentile_ranks(str(end_date))
                            total_updated += count
                        
                        print(f"✓ 分位数排名已更新，共 {total_updated} 条记录")
                    except Exception as e:
                        print(f"⚠️  更新分位数失败: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"✓ 数据库已有全部 {len(existing_quarters)} 个季度的核心指标，无需更新")
            else:
                print("⚠️  未能计算出核心指标")
        else:
            print("⚠️  缺少必要的财务数据，无法计算核心指标")
    except Exception as e:
        print(f"⚠️  计算核心指标失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 生成核心指标分析报告
    print("\n" + "="*60)
    print("生成核心指标分析报告...")
    print("="*60)
    
    try:
        from final_report_generator_echarts import FinalReportGenerator
        
        core_generator = FinalReportGenerator()
        
        # 生成报告，使用新的文件名格式
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        core_report_path = f"data/{ts_code}_核心指标_{timestamp}.html"
        core_generator.generate_report(ts_code, output_path=core_report_path)
        
        print(f"✓ 核心指标报告已生成")
        print(f"  提示: 在浏览器中打开该文件即可查看交互式核心指标分析报告")
    except Exception as e:
        print(f"⚠️  生成核心指标报告失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n完成！数据已保存到 {args.output_dir}")


if __name__ == '__main__':
    main()
