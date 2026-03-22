"""
主程序：从 Tushare 获取公司财务数据
"""

import argparse
from datetime import datetime
from financial_data_manager import FinancialDataManager, normalize_stock_code
from balance_sheet_restructure import restructure_balance_sheet, transpose_data
from income_statement_restructure import restructure_income_statement
from cashflow_statement_restructure import restructure_cashflow_statement
from annual_report_generator import AnnualReportGenerator
from excel_styled_exporter import save_balance_sheet_to_excel_styled
import os
import yaml
import pandas as pd


def transpose_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    转置财务数据：将字段横向、时间纵向的格式转换为字段纵向、时间横向的格式
    
    Args:
        df: 原始数据（字段横向，时间纵向）
        
    Returns:
        转置后的数据（字段纵向，时间横向）
    """
    if df is None or len(df) == 0:
        return df
    
    # 找到日期列
    date_col = None
    for col in ['end_date', '报告期']:
        if col in df.columns:
            date_col = col
            break
    
    if date_col is None:
        return df
    
    # 设置日期为索引
    df_copy = df.copy()
    df_copy = df_copy.set_index(date_col)
    
    # 转置
    df_transposed = df_copy.T
    
    # 重置索引，将字段名作为一列
    df_transposed = df_transposed.reset_index()
    df_transposed = df_transposed.rename(columns={'index': '项目'})
    
    return df_transposed


def add_total_share_to_balance(df_balance: pd.DataFrame, total_share_df: pd.DataFrame) -> pd.DataFrame:
    """
    将总股本数据添加到资产负债表中
    
    Args:
        df_balance: 重构后的资产负债表
        total_share_df: 总股本数据DataFrame（从数据库读取）
        
    Returns:
        添加了总股本行的资产负债表
    """
    if total_share_df is None or len(total_share_df) == 0:
        return df_balance
    
    # 创建总股本字典
    total_share_dict = {}
    for _, row in total_share_df.iterrows():
        total_share_dict[str(row['end_date'])] = row['total_share']
    
    # 创建总股本行
    total_share_row = {'项目': '总股本'}
    
    # 获取所有日期列
    date_columns = [col for col in df_balance.columns if col != '项目']
    
    for col in date_columns:
        # 将列名转换为YYYYMMDD格式
        col_key = col.replace('/', '').replace('-', '').replace('Q3-TTM', '')
        if 'TTM' in col:
            col_key = col[:4] + '1231'  # TTM使用当年12月31日
        
        total_share_row[col] = total_share_dict.get(col_key)
    
    # 将总股本行添加到资产负债表末尾
    df_result = pd.concat([df_balance, pd.DataFrame([total_share_row])], ignore_index=True)
    
    return df_result



def main():
    """主函数 - 从数据库读取财务数据并生成分析报告"""
    parser = argparse.ArgumentParser(description='从本地数据库读取财务数据并生成分析报告')
    parser.add_argument('ts_code', type=str, help='股票代码（例如：000333 或 600519.SH）')
    parser.add_argument('--start-date', type=str, help='开始日期（YYYYMMDD）- 筛选数据库中的数据')
    parser.add_argument('--end-date', type=str, help='结束日期（YYYYMMDD）- 筛选数据库中的数据')
    parser.add_argument('--output-dir', type=str, default='./data', help='数据输出目录')
    parser.add_argument('--format', type=str, choices=['csv', 'excel', 'both'], 
                       default='csv', help='输出格式（csv/excel/both）')
    parser.add_argument('--db-path', type=str, default='database/financial_data.db', 
                       help='数据库路径')
    parser.add_argument('--annual-ttm', action='store_true', default=True,
                       help='生成年报+TTM重构报表（默认开启，使用--no-annual-ttm关闭）')
    parser.add_argument('--no-annual-ttm', action='store_true',
                       help='不生成年报+TTM数据')
    parser.add_argument('--years', type=int, default=None, 
                       help='年报年数（默认覆盖所有历史数据）')
    parser.add_argument('--save-dividend-excel', action='store_true',
                       help='将分红数据保存为Excel文件')
    
    args = parser.parse_args()
    
    # 规范化股票代码（自动补全交易所后缀）
    ts_code = normalize_stock_code(args.ts_code)
    
    # 初始化数据库管理器
    print(f"连接数据库: {args.db_path}")
    db_manager = FinancialDataManager(args.db_path)
    
    # 检查数据完整性
    print(f"\n检查 {ts_code} 的数据...")
    data_exists = {}
    for table in ['balancesheet', 'income', 'cashflow', 'fina_indicator']:
        df = db_manager.get_financial_data(ts_code, table, args.start_date, args.end_date)
        data_exists[table] = len(df) > 0
        if len(df) > 0:
            print(f"  ✓ {table}: {len(df)} 条记录")
        else:
            print(f"  ✗ {table}: 无数据")
    
    # 如果没有任何数据，提示用户
    if not any(data_exists.values()):
        print(f"\n❌ 错误：数据库中没有 {ts_code} 的财务数据")
        print(f"\n请先运行以下命令采集数据:")
        print(f"  python update_financial_data.py --init")
        print(f"\n或者只采集单只股票:")
        print(f"  # 修改 update_financial_data.py 中的股票列表")
        return
    
    # 从数据库读取财务数据
    print(f"\n从数据库读取 {ts_code} 的财务数据...")
    data = {}
    
    # 生成统一的时间戳（用于所有输出文件）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for table_name in ['balancesheet', 'income', 'cashflow', 'fina_indicator']:
        df = db_manager.get_financial_data(ts_code, table_name, args.start_date, args.end_date)
        if len(df) > 0:
            data[table_name] = df
            print(f"  ✓ {table_name}: {len(df)} 条记录")
    
    # 注：总股本数据已从资产负债表中直接获取，不需要单独读取
    
    # 读取分红数据
    print(f"\n读取分红送股数据...")
    dividend_df = db_manager.get_dividend_data(ts_code, args.start_date, args.end_date)
    if len(dividend_df) > 0:
        print(f"  ✓ 分红数据: {len(dividend_df)} 条记录")
        data['dividend'] = dividend_df
        
        # 如果用户要求，保存分红数据为Excel
        if args.save_dividend_excel:
            os.makedirs(args.output_dir, exist_ok=True)
            excel_filename = os.path.join(args.output_dir, f"{ts_code}_分红送股_{timestamp}.xlsx")
            dividend_df.to_excel(excel_filename, index=False)
            print(f"  ✓ 分红数据已保存到: {excel_filename}")
    else:
        print(f"  ⚠️  分红数据: 无数据")
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 重构资产负债表
    if data.get('balancesheet') is not None and len(data['balancesheet']) > 0:
        print(f"\n重构资产负债表...")
        try:
            # 获取原始资产负债表数据并转置
            df_balance = data['balancesheet'].copy()
            df_transposed = transpose_data(df_balance)
            
            # 重构资产负债表（总股本已包含在资产负债表的 data_json 中）
            df_restructured = restructure_balance_sheet(df_transposed, ts_code=ts_code)
            
            # 保存重构后的数据
            restructured_filename = os.path.join(args.output_dir, f"{ts_code}_balancesheet_restructured_{timestamp}.csv")
            df_restructured.to_csv(restructured_filename, index=False, encoding='utf-8-sig')
            print(f"✓ 重构后的资产负债表已保存到: {restructured_filename}")
            
            # 添加到data字典
            data['balancesheet_restructured'] = df_restructured
            
            # 如果需要Excel格式，也保存Excel（带样式）
            if args.format in ['excel', 'both']:
                excel_filename = os.path.join(args.output_dir, f"{ts_code}_balancesheet_restructured_{timestamp}.xlsx")
                save_balance_sheet_to_excel_styled(df_restructured, excel_filename)
                print(f"✓ Excel格式已保存到: {excel_filename}")
        except Exception as e:
            print(f"⚠️  资产负债表重构失败: {e}")
    
    # 重构利润表
    if data.get('income') is not None and len(data['income']) > 0:
        print(f"\n重构利润表（股权价值增加表）...")
        try:
            # 从 config.yaml 读取股权资本成本率，缺失时默认 8%
            equity_cost_rate = 0.08
            config_path = args.db_path.replace('database/financial_data.db', 'config.yaml')
            if not os.path.isabs(config_path):
                config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    _cfg = yaml.safe_load(f) or {}
                equity_cost_rate = _cfg.get('restructure', {}).get('equity_cost_rate', 0.08)
            print(f"  股权资本成本率: {equity_cost_rate*100:.1f}%")
            
            # 获取原始利润表数据并转置
            df_income = data['income'].copy()
            df_transposed = transpose_data(df_income)
            
            # 获取资产负债表重构数据（用于获取所有者权益合计）
            balance_restructured = data.get('balancesheet_restructured')
            
            # 重构利润表
            df_restructured = restructure_income_statement(
                df_transposed, 
                equity_data=balance_restructured,
                equity_cost_rate=equity_cost_rate
            )
            
            # 保存重构后的数据
            restructured_filename = os.path.join(args.output_dir, f"{ts_code}_income_restructured_{timestamp}.csv")
            df_restructured.to_csv(restructured_filename, index=False, encoding='utf-8-sig')
            print(f"✓ 重构后的利润表已保存到: {restructured_filename}")
            
            # 添加到data字典
            data['income_restructured'] = df_restructured
            
            # 如果需要Excel格式，也保存Excel
            if args.format in ['excel', 'both']:
                excel_filename = os.path.join(args.output_dir, f"{ts_code}_income_restructured_{timestamp}.xlsx")
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
            df_transposed = transpose_data(df_cashflow)
            
            # 获取利润表原始数据并转置(用于营业收入、营业总成本)
            income_original = None
            if data.get('income') is not None:
                income_original = transpose_data(data['income'].copy())
            
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
            restructured_filename = os.path.join(args.output_dir, f"{ts_code}_cashflow_restructured_{timestamp}.csv")
            df_restructured.to_csv(restructured_filename, index=False, encoding='utf-8-sig')
            print(f"✓ 重构后的现金流量表已保存到: {restructured_filename}")
            
            # 添加到data字典
            data['cashflow_restructured'] = df_restructured
            
            # 如果需要Excel格式,也保存Excel
            if args.format in ['excel', 'both']:
                excel_filename = os.path.join(args.output_dir, f"{ts_code}_cashflow_restructured_{timestamp}.xlsx")
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
                        # 找到最早和最新的年份（将列名转为字符串）
                        years_list = [int(str(col)[:4]) for col in date_cols if len(str(col)) >= 4 and str(col)[:4].isdigit()]
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
                        csv_filename = os.path.join(args.output_dir, f"{ts_code}_{report_name}_annual_ttm_{timestamp}.csv")
                        df_formatted.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                        print(f"✓ {report_name}年报+TTM已保存到: {csv_filename}")
                        
                        # 添加到data字典
                        data[f'{report_name}_annual_ttm'] = df_formatted
                        
                        # 如果需要Excel格式，也保存Excel
                        if args.format in ['excel', 'both']:
                            excel_filename = os.path.join(args.output_dir, f"{ts_code}_{report_name}_annual_ttm_{timestamp}.xlsx")
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
            from html_report_generator import FinancialStatementsReportGenerator
            
            # 检查是否有年报+TTM数据
            balance_ttm = data.get('balance_sheet_annual_ttm')
            income_ttm = data.get('income_statement_annual_ttm')
            cashflow_ttm = data.get('cashflow_statement_annual_ttm')
            
            if balance_ttm is not None and income_ttm is not None and cashflow_ttm is not None:
                # 从数据库 stock_list 查询公司名称，查不到则使用股票代码前缀
                _stocks = db_manager.get_all_stocks()
                _name_map = {s['ts_code']: s['name'] for s in _stocks if s.get('name')}
                company_name = _name_map.get(ts_code, ts_code.split('.')[0])
                
                # 生成HTML报告
                html_filename = os.path.join(args.output_dir, f"{ts_code}_financial_report_{timestamp}.html")
                generator = FinancialStatementsReportGenerator(company_name=company_name, stock_code=ts_code)
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
    
    # 检查核心指标（不再自动计算和保存）
    print("\n" + "="*60)
    print("检查核心指标...")
    print("="*60)
    
    # 若存在公司特定重分类规则，重算 lta_turnover_log 并更新数据库
    try:
        from balance_sheet_reclassifier import recalculate_lta_after_reclassification, load_company_rules
        company_rules = load_company_rules(ts_code)
        if company_rules and company_rules.get('reclassify'):
            balance_raw = data.get('balancesheet')
            income_raw = data.get('income')
            balance_restructured = data.get('balancesheet_restructured')
            if balance_raw is not None and income_raw is not None:
                print(f"  检测到 {ts_code} 存在重分类规则，重算 lta_turnover_log...")
                updated = recalculate_lta_after_reclassification(
                    ts_code, balance_raw, income_raw, db_manager,
                    balance_restructured=balance_restructured
                )
                if updated > 0:
                    print(f"  ✓ 已更新 {updated} 期 lta_turnover_log（含分位数排名）")
                else:
                    print(f"  ⚠️  lta_turnover_log 无可更新记录（可能尚未生成核心指标）")
    except Exception as e:
        print(f"  ⚠️  重算 lta_turnover_log 失败: {e}")
        import traceback
        traceback.print_exc()

    try:
        # 获取三大报表数据
        balance_data = data.get('balancesheet')
        income_data = data.get('income')
        cashflow_data = data.get('cashflow')
        
        if balance_data is not None and income_data is not None and cashflow_data is not None:
            conn = db_manager.get_connection()
            
            # 1. 检查年报核心指标
            existing_annual_query = '''
                SELECT DISTINCT end_date 
                FROM core_indicators 
                WHERE ts_code = ? AND ar_turnover_log IS NOT NULL AND is_ttm = 0
            '''
            existing_annual_df = pd.read_sql_query(existing_annual_query, conn, params=(ts_code,))
            existing_annual = set(existing_annual_df['end_date'].tolist()) if len(existing_annual_df) > 0 else set()
            
            # 获取数据库中有财务数据的所有年报季度
            db_annual_query = '''
                SELECT DISTINCT b.end_date 
                FROM balancesheet b
                INNER JOIN income i ON b.ts_code = i.ts_code AND b.end_date = i.end_date
                INNER JOIN cashflow c ON b.ts_code = c.ts_code AND b.end_date = c.end_date
                WHERE b.ts_code = ? AND b.end_date LIKE '%1231'
            '''
            db_annual_df = pd.read_sql_query(db_annual_query, conn, params=(ts_code,))
            all_annual = set(db_annual_df['end_date'].tolist()) if len(db_annual_df) > 0 else set()
            
            missing_annual = all_annual - existing_annual
            
            if len(missing_annual) == 0:
                print(f"✓ 年报核心指标: 已有全部 {len(existing_annual)} 个年报的核心指标")
            else:
                print(f"⚠️  年报核心指标: 发现 {len(missing_annual)} 个年报缺少核心指标")
                print(f"   已有: {len(existing_annual)} 个年报")
                print(f"   缺失: {sorted(list(missing_annual))[:5]}{'...' if len(missing_annual) > 5 else ''}")
            
            # 2. 检查 TTM 指标
            # 获取最新季度
            date_col = '报告期' if '报告期' in balance_data.columns else 'end_date'
            latest_quarter = sorted([str(q).replace('-', '') for q in balance_data[date_col].unique()])[-1]
            
            # 判断最新季度是否为年报
            is_annual = latest_quarter.endswith('1231')
            
            if not is_annual:
                # 非年报季度，检查是否有 TTM 指标
                ttm_query = '''
                    SELECT end_date, ar_turnover_log, gross_margin
                    FROM core_indicators
                    WHERE ts_code = ? AND end_date = ? AND is_ttm = 1
                '''
                ttm_df = pd.read_sql_query(ttm_query, conn, params=(ts_code, latest_quarter))
                
                if len(ttm_df) > 0:
                    print(f"✓ TTM 指标: 最新季度 {latest_quarter} 已有 TTM 核心指标")
                else:
                    print(f"⚠️  TTM 指标: 最新季度 {latest_quarter} 缺少 TTM 核心指标")
                    print(f"\n💡 建议运行以下命令生成 TTM 指标:")
                    print(f"   python3 backfill_ttm_indicators.py --stocks {ts_code}")
            else:
                print(f"✓ 最新季度 {latest_quarter} 为年报，无需 TTM 指标")
            
            # 3. 如果有缺失，给出建议
            if len(missing_annual) > 0:
                print(f"\n💡 建议运行以下命令更新核心指标:")
                print(f"   python3 update_financial_data.py --update-latest")
                print(f"   或")
                print(f"   python3 recalc_single_stock.py {ts_code.split('.')[0]}")
        else:
            print("⚠️  缺少必要的财务数据，无法检查核心指标")
    except Exception as e:
        print(f"⚠️  检查核心指标失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 生成核心指标分析报告
    print("\n" + "="*60)
    print("生成核心指标分析报告...")
    print("="*60)
    
    try:
        from final_report_generator_echarts import CoreIndicatorsReportGenerator
        
        core_generator = CoreIndicatorsReportGenerator()
        
        # 生成报告，使用统一的时间戳格式
        core_report_path = f"{args.output_dir}/{ts_code}_核心指标_{timestamp}.html"
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
