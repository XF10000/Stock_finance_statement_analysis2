"""
年报和TTM数据生成器
生成过去10年年报 + 最新一期TTM的重构报表
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging


class AnnualReportGenerator:
    """年报和TTM数据生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_annual_reports_with_ttm(
        self,
        balance_restructured: pd.DataFrame,
        income_restructured: pd.DataFrame,
        cashflow_restructured: pd.DataFrame,
        years: int = 10
    ) -> Dict[str, pd.DataFrame]:
        """
        生成年报+TTM的重构报表
        
        Args:
            balance_restructured: 重构后的资产负债表
            income_restructured: 重构后的利润表
            cashflow_restructured: 重构后的现金流量表
            years: 年数，默认10年
            
        Returns:
            包含三大报表的字典
        """
        # 获取最新报告期
        all_dates = self._get_all_dates(balance_restructured, income_restructured, cashflow_restructured)
        if not all_dates:
            self.logger.error("无法获取报告期数据")
            return {}
        
        latest_date = max(all_dates)
        latest_year = int(latest_date[:4])
        latest_month = int(latest_date[4:6])
        
        self.logger.info(f"最新报告期: {latest_date} (年份: {latest_year}, 月份: {latest_month})")
        
        # 判断最新季度
        latest_quarter = self._get_quarter(latest_date)
        self.logger.info(f"最新季度: Q{latest_quarter}")
        
        # 确定年度范围
        # 如果最新是Q4，则年度范围是 (latest_year-years) 到 latest_year
        # 如果最新是Q1-Q3，则年度范围是 (latest_year-years) 到 (latest_year-1)
        if latest_quarter == 4:
            start_year = latest_year - years
            end_year = latest_year
        else:
            start_year = latest_year - years
            end_year = latest_year - 1
        
        self.logger.info(f"年报年度范围: {start_year} - {end_year}")
        
        # 提取年报数据（按降序排列：从新到旧）
        annual_dates = [f"{year}1231" for year in range(end_year, start_year - 1, -1)]
        
        # 生成资产负债表年报+TTM
        balance_annual_ttm = self._generate_balance_sheet_annual_with_ttm(
            balance_restructured, annual_dates, latest_date, latest_quarter
        )
        
        # 生成利润表年报+TTM
        income_annual_ttm = self._generate_income_statement_annual_with_ttm(
            income_restructured, annual_dates, latest_date, latest_quarter
        )
        
        # 生成现金流量表年报+TTM
        cashflow_annual_ttm = self._generate_cashflow_statement_annual_with_ttm(
            cashflow_restructured, annual_dates, latest_date, latest_quarter
        )
        
        return {
            'balance_sheet': balance_annual_ttm,
            'income_statement': income_annual_ttm,
            'cashflow_statement': cashflow_annual_ttm
        }
    
    def _get_all_dates(self, *dfs: pd.DataFrame) -> List[str]:
        """获取所有报表中的日期"""
        all_dates = set()
        
        for df in dfs:
            if df is not None and len(df) > 0:
                # 获取非"项目"列，并转换为字符串
                date_cols = [str(col) for col in df.columns if col != '项目']
                all_dates.update(date_cols)
        
        return sorted(list(all_dates))
    
    def _get_quarter(self, date_str: str) -> int:
        """根据日期字符串判断季度"""
        month = int(date_str[4:6])
        if month == 3:
            return 1
        elif month == 6:
            return 2
        elif month == 9:
            return 3
        elif month == 12:
            return 4
        else:
            return 0
    
    def _generate_balance_sheet_annual_with_ttm(
        self,
        df: pd.DataFrame,
        annual_dates: List[str],
        latest_date: str,
        latest_quarter: int
    ) -> pd.DataFrame:
        """
        生成资产负债表年报+TTM数据
        
        资产负债表是时点数据，不需要计算TTM
        如果最新是Q4，直接使用年报数据
        如果最新是Q1-Q3，使用最新季度数据作为TTM
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        self.logger.info("生成资产负债表年报+TTM数据...")
        
        # 确保所有列名都是字符串类型（避免整数列名导致的匹配失败）
        df = df.copy()
        df.columns = [str(col) for col in df.columns]
        
        # 构建输出的列顺序
        output_columns = ['项目']
        
        # 如果最新是Q4，年报数据中已包含最新数据
        if latest_quarter == 4:
            # 只保留年报数据
            output_columns.extend(annual_dates)
            self.logger.info(f"最新为Q4，使用年报数据: {latest_date}")
        else:
            # 添加TTM列（使用最新季度数据）
            ttm_label = f"{latest_date[:4]}Q{latest_quarter}-TTM"
            output_columns.append(ttm_label)
            output_columns.extend(annual_dates)
            self.logger.info(f"最新为Q{latest_quarter}，添加TTM列: {ttm_label}")
        
        # 构建结果DataFrame
        result_data = {}
        
        # 获取所有可用的日期列（按降序排列，转换为字符串）
        all_date_cols = sorted([str(col) for col in df.columns if col != '项目'], reverse=True)
        
        for _, row in df.iterrows():
            item_name = row['项目']
            result_data[item_name] = {}
            
            # 添加TTM数据（如果不是Q4）
            if latest_quarter != 4:
                # 尝试获取最新季度的数据
                value = row.get(latest_date, np.nan) if latest_date in df.columns else np.nan
                
                # 如果最新季度数据为空，向前查找最近一期有数据的季度
                if pd.isna(value):
                    for date_col in all_date_cols:
                        if date_col <= latest_date:  # 只查找不晚于最新日期的数据
                            temp_value = row.get(date_col, np.nan)
                            if pd.notna(temp_value):
                                value = temp_value
                                self.logger.debug(f"{item_name}: {latest_date}数据为空，使用{date_col}的数据")
                                break
                
                result_data[item_name][ttm_label] = value
            
            # 添加年报数据
            for date in annual_dates:
                if date in df.columns:
                    result_data[item_name][date] = row.get(date, np.nan)
                else:
                    result_data[item_name][date] = np.nan
        
        # 转换为DataFrame
        df_result = pd.DataFrame(result_data).T
        df_result = df_result.reset_index()
        df_result.columns = output_columns
        
        return df_result
    
    def _generate_income_statement_annual_with_ttm(
        self,
        df: pd.DataFrame,
        annual_dates: List[str],
        latest_date: str,
        latest_quarter: int
    ) -> pd.DataFrame:
        """
        生成利润表年报+TTM数据
        
        利润表是期间数据（累计值），需要计算TTM
        TTM = 今年Q累计 - 去年同Q累计 + 去年Q4累计
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        self.logger.info("生成利润表年报+TTM数据...")
        
        # 确保所有列名都是字符串类型
        df = df.copy()
        df.columns = [str(col) for col in df.columns]
        
        # 构建输出的列顺序
        output_columns = ['项目']
        
        # 如果最新是Q4，年报数据中已包含最新数据
        if latest_quarter == 4:
            output_columns.extend(annual_dates)
            self.logger.info(f"最新为Q4，使用年报数据: {latest_date}")
        else:
            # 添加TTM列
            ttm_label = f"{latest_date[:4]}Q{latest_quarter}-TTM"
            output_columns.append(ttm_label)
            output_columns.extend(annual_dates)
            self.logger.info(f"最新为Q{latest_quarter}，计算TTM: {ttm_label}")
        
        # 计算TTM需要的日期
        if latest_quarter != 4:
            latest_year = int(latest_date[:4])
            last_year = latest_year - 1
            
            # 今年Q累计
            current_q_date = latest_date
            
            # 去年同Q累计
            last_year_same_q_date = f"{last_year}{latest_date[4:]}"
            
            # 去年Q4累计
            last_year_q4_date = f"{last_year}1231"
            
            self.logger.info(f"TTM计算日期: 当前={current_q_date}, 去年同期={last_year_same_q_date}, 去年Q4={last_year_q4_date}")
        
        # 构建结果DataFrame
        result_data = {}
        
        for _, row in df.iterrows():
            item_name = row['项目']
            result_data[item_name] = {}
            
            # 计算TTM（如果不是Q4）
            if latest_quarter != 4:
                ttm_value = self._calculate_ttm(
                    row, current_q_date, last_year_same_q_date, last_year_q4_date, item_name
                )
                result_data[item_name][ttm_label] = ttm_value
            
            # 添加年报数据
            for date in annual_dates:
                if date in df.columns:
                    result_data[item_name][date] = row.get(date, np.nan)
                else:
                    result_data[item_name][date] = np.nan
        
        # 转换为DataFrame
        df_result = pd.DataFrame(result_data).T
        df_result = df_result.reset_index()
        df_result.columns = output_columns
        
        # 重新计算TTM的比率类指标（如果有TTM列）
        if latest_quarter != 4:
            self._recalculate_income_ratios(df_result, ttm_label)
        
        return df_result
    
    def _recalculate_income_ratios(self, df: pd.DataFrame, ttm_col: str):
        """
        重新计算利润表中的比率类指标
        
        比率类指标不能用TTM公式（加减法）计算，必须用对应的分子/分母重新计算
        """
        def get_value(item_name):
            row = df[df['项目'] == item_name]
            if len(row) > 0 and ttm_col in df.columns:
                val = row[ttm_col].values[0]
                return val if pd.notna(val) else 0
            return 0
        
        def set_value(item_name, value):
            df.loc[df['项目'] == item_name, ttm_col] = value
        
        # 获取基础数据
        营业收入 = get_value('营业收入')
        营业成本 = get_value('营业成本')
        毛利 = get_value('毛利')
        税金及附加 = get_value('税金及附加')
        销售费用 = get_value('销售费用')
        管理费用 = get_value('管理费用')
        研发费用 = get_value('研发费用')
        资产减值损失 = get_value('资产减值损失')
        信用减值损失 = get_value('信用减值损失')
        净利润 = get_value('净利润')
        
        # 重新计算比率
        if 营业收入 != 0:
            set_value('营业成本率', 营业成本 / 营业收入)
            set_value('毛利率', 毛利 / 营业收入)
            set_value('营业税金及附加率', 税金及附加 / 营业收入)
            set_value('销售费用率', 销售费用 / 营业收入)
            set_value('管理费用率', 管理费用 / 营业收入)
            set_value('研发费用率', 研发费用 / 营业收入)
            set_value('资产减值损失率', (资产减值损失 + 信用减值损失) / 营业收入)
            set_value('净利润率', 净利润 / 营业收入)
            
            # 其他可能的比率指标
            息税前经营利润 = get_value('息税前经营利润')
            if 息税前经营利润 != 0:
                set_value('息税前经营利润率', 息税前经营利润 / 营业收入)
    
    def _generate_cashflow_statement_annual_with_ttm(
        self,
        df: pd.DataFrame,
        annual_dates: List[str],
        latest_date: str,
        latest_quarter: int
    ) -> pd.DataFrame:
        """
        生成现金流量表年报+TTM数据
        
        现金流量表是期间数据（累计值），需要计算TTM
        TTM = 今年Q累计 - 去年同Q累计 + 去年Q4累计
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        self.logger.info("生成现金流量表年报+TTM数据...")
        
        # 确保所有列名都是字符串类型
        df = df.copy()
        df.columns = [str(col) for col in df.columns]
        
        # 构建输出的列顺序
        output_columns = ['项目']
        
        # 如果最新是Q4，年报数据中已包含最新数据
        if latest_quarter == 4:
            output_columns.extend(annual_dates)
            self.logger.info(f"最新为Q4，使用年报数据: {latest_date}")
        else:
            # 添加TTM列
            ttm_label = f"{latest_date[:4]}Q{latest_quarter}-TTM"
            output_columns.append(ttm_label)
            output_columns.extend(annual_dates)
            self.logger.info(f"最新为Q{latest_quarter}，计算TTM: {ttm_label}")
        
        # 计算TTM需要的日期
        if latest_quarter != 4:
            latest_year = int(latest_date[:4])
            last_year = latest_year - 1
            
            # 今年Q累计
            current_q_date = latest_date
            
            # 去年同Q累计
            last_year_same_q_date = f"{last_year}{latest_date[4:]}"
            
            # 去年Q4累计
            last_year_q4_date = f"{last_year}1231"
            
            self.logger.info(f"TTM计算日期: 当前={current_q_date}, 去年同期={last_year_same_q_date}, 去年Q4={last_year_q4_date}")
        
        # 构建结果DataFrame
        result_data = {}
        
        for _, row in df.iterrows():
            item_name = row['项目']
            result_data[item_name] = {}
            
            # 计算TTM（如果不是Q4）
            if latest_quarter != 4:
                ttm_value = self._calculate_ttm(
                    row, current_q_date, last_year_same_q_date, last_year_q4_date, item_name
                )
                result_data[item_name][ttm_label] = ttm_value
            
            # 添加年报数据
            for date in annual_dates:
                if date in df.columns:
                    result_data[item_name][date] = row.get(date, np.nan)
                else:
                    result_data[item_name][date] = np.nan
        
        # 转换为DataFrame
        df_result = pd.DataFrame(result_data).T
        df_result = df_result.reset_index()
        df_result.columns = output_columns
        
        return df_result
    
    def _calculate_ttm(
        self,
        row: pd.Series,
        current_q_date: str,
        last_year_same_q_date: str,
        last_year_q4_date: str,
        item_name: str
    ) -> float:
        """
        计算TTM值
        
        TTM = 今年Q累计 - 去年同Q累计 + 去年Q4累计
        
        Args:
            row: 数据行
            current_q_date: 今年Q累计日期
            last_year_same_q_date: 去年同Q累计日期
            last_year_q4_date: 去年Q4累计日期
            item_name: 项目名称
            
        Returns:
            TTM值
        """
        # 获取值
        current_value = row.get(current_q_date, np.nan)
        last_year_same_q_value = row.get(last_year_same_q_date, np.nan)
        last_year_q4_value = row.get(last_year_q4_date, np.nan)
        
        # 检查是否有足够的有效值
        if pd.isna(current_value) or pd.isna(last_year_q4_value):
            return np.nan
        
        # 如果去年同Q数据为空，说明是Q1数据
        # Q1的TTM = Q1累计 - 0 + 去年Q4累计
        if pd.isna(last_year_same_q_value):
            last_year_same_q_value = 0
        
        # 计算TTM
        ttm = current_value - last_year_same_q_value + last_year_q4_value
        
        return ttm
    
    def format_annual_report(self, df: pd.DataFrame, statement_type: str) -> pd.DataFrame:
        """
        格式化年报报表，使其更易读
        
        Args:
            df: 年报数据
            statement_type: 报表类型（balance_sheet, income_statement, cashflow_statement）
            
        Returns:
            格式化后的DataFrame
        """
        if df is None or len(df) == 0:
            return df
        
        # 格式化日期列名
        df_formatted = df.copy()
        
        # 重命名日期列
        new_columns = {}
        for col in df_formatted.columns:
            if col == '项目':
                new_columns[col] = col
            elif col.endswith('-TTM'):
                new_columns[col] = col
            else:
                # 将 YYYYMMDD 转换为 YYYY/MM/DD
                if len(col) == 8 and col.isdigit():
                    formatted_date = f"{col[:4]}/{col[4:6]}/{col[6:8]}"
                    new_columns[col] = formatted_date
                else:
                    new_columns[col] = col
        
        df_formatted = df_formatted.rename(columns=new_columns)
        
        return df_formatted


# ============================================================================
# 主函数测试
# ============================================================================

if __name__ == '__main__':
    import sys
    import os
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 测试数据路径
    data_dir = 'data'
    ts_code = '603345.SH'
    
    # 读取重构后的数据
    balance_file = os.path.join(data_dir, f'{ts_code}_balancesheet_restructured.csv')
    income_file = os.path.join(data_dir, f'{ts_code}_income_restructured.csv')
    cashflow_file = os.path.join(data_dir, f'{ts_code}_cashflow_restructured.csv')
    
    print("读取重构后的数据...")
    df_balance = pd.read_csv(balance_file, encoding='utf-8-sig')
    df_income = pd.read_csv(income_file, encoding='utf-8-sig')
    df_cashflow = pd.read_csv(cashflow_file, encoding='utf-8-sig')
    
    print(f"资产负债表: {df_balance.shape}")
    print(f"利润表: {df_income.shape}")
    print(f"现金流量表: {df_cashflow.shape}")
    
    # 生成年报+TTM数据
    generator = AnnualReportGenerator()
    reports = generator.generate_annual_reports_with_ttm(
        df_balance, df_income, df_cashflow, years=10
    )
    
    # 格式化并保存
    for report_name, df_report in reports.items():
        if df_report is not None and len(df_report) > 0:
            # 格式化
            df_formatted = generator.format_annual_report(df_report, report_name)
            
            # 保存
            output_file = os.path.join(data_dir, f'{ts_code}_{report_name}_annual_ttm.csv')
            df_formatted.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n✓ {report_name} 已保存到: {output_file}")
            
            # 显示前几行
            print(f"\n{report_name} 前5行:")
            print(df_formatted.head().to_string())
