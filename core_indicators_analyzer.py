"""
四大核心财务指标分析器

计算以下四大核心指标：
1. 报表逻辑一致性检验暨回款周期
   - 应收账款周转率对数 = ln(TTM营业收入 / 平均应收账款)
   - 毛利率 = (营业收入 - 营业成本) / 营业收入
2. 再投资质量暨跑冒滴漏风险检验
   - 长期经营资产周转率对数 = ln(TTM营业收入 / 平均长期经营资产)
3. 产业链地位检验暨资金运用能力
   - 净营运资本比率 = 净营运资本 / 资产总额 × 100%
4. 真实盈利水平暨现金流创造能力
   - 经营现金流比率 = 经营活动现金流量净额 / 资产总额 × 100%
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging
from datetime import datetime


class CoreIndicatorsAnalyzer:
    """核心财务指标分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.logger = logging.getLogger(__name__)
    
    def calculate_all_indicators(
        self,
        balance_sheet: pd.DataFrame,
        income_statement: pd.DataFrame,
        cashflow_statement: pd.DataFrame,
        is_ttm_data: bool = False
    ) -> pd.DataFrame:
        """
        计算所有核心指标
        
        Args:
            balance_sheet: 资产负债表数据
            income_statement: 利润表数据
            cashflow_statement: 现金流量表数据
            is_ttm_data: 数据是否已经是 TTM 格式（如果是，直接使用当期值而不再计算 TTM）
            
        Returns:
            包含所有指标的DataFrame
        """
        # 确保所有列名都是字符串类型（避免整数列名导致的匹配失败）
        balance_sheet = balance_sheet.copy()
        balance_sheet.columns = [str(col) for col in balance_sheet.columns]
        
        income_statement = income_statement.copy()
        income_statement.columns = [str(col) for col in income_statement.columns]
        
        cashflow_statement = cashflow_statement.copy()
        cashflow_statement.columns = [str(col) for col in cashflow_statement.columns]
        
        # 1. 找出三大报表都有数据的报告期
        common_dates = self._get_common_dates(
            balance_sheet, income_statement, cashflow_statement
        )
        
        if len(common_dates) == 0:
            self.logger.warning("没有找到三大报表都有数据的报告期")
            return pd.DataFrame()
        
        self.logger.info(f"找到 {len(common_dates)} 个有效报告期")
        
        # 2. 筛选数据
        balance_filtered = self._filter_by_dates(balance_sheet, common_dates)
        income_filtered = self._filter_by_dates(income_statement, common_dates)
        cashflow_filtered = self._filter_by_dates(cashflow_statement, common_dates)
        
        # 3. 计算TTM营业收入、营业成本、经营现金流
        if is_ttm_data:
            # 数据已经是 TTM 格式，直接使用当期值
            revenue_col = '营业收入' if '营业收入' in income_filtered.columns else 'revenue'
            ttm_revenue = self._use_current_values(income_filtered, revenue_col)
            
            cost_col = '营业成本' if '营业成本' in income_filtered.columns else 'oper_cost'
            ttm_cost = self._use_current_values(income_filtered, cost_col)
            
            ocf_col = '经营活动产生的现金流量净额' if '经营活动产生的现金流量净额' in cashflow_filtered.columns else 'n_cashflow_act'
            ttm_ocf = self._use_current_values(cashflow_filtered, ocf_col)
        else:
            # 原有逻辑：计算 TTM
            ttm_revenue = self._calculate_ttm_revenue(income_filtered)
            
            cost_col = '营业成本' if '营业成本' in income_filtered.columns else 'oper_cost'
            ttm_cost = self._calculate_ttm_metric(income_filtered, cost_col)
            
            ocf_col = '经营活动产生的现金流量净额' if '经营活动产生的现金流量净额' in cashflow_filtered.columns else 'n_cashflow_act'
            ttm_ocf = self._calculate_ttm_metric(cashflow_filtered, ocf_col)
        
        # 4. 计算各项指标
        results = []
        
        for date in sorted(common_dates):
            try:
                indicators = self._calculate_indicators_for_date(
                    date,
                    balance_filtered,
                    income_filtered,
                    cashflow_filtered,
                    ttm_revenue,
                    ttm_cost,
                    ttm_ocf
                )
                
                if indicators:
                    results.append(indicators)
                    
            except Exception as e:
                self.logger.error(f"计算 {date} 的指标时出错: {str(e)}")
                continue
        
        if len(results) == 0:
            self.logger.warning("没有成功计算任何指标")
            return pd.DataFrame()
        
        # 转换为DataFrame
        df_results = pd.DataFrame(results)
        
        # 按日期排序
        df_results = df_results.sort_values('报告期')
        
        self.logger.info(f"成功计算 {len(df_results)} 期指标")
        
        return df_results
    
    def _get_common_dates(
        self,
        balance_sheet: pd.DataFrame,
        income_statement: pd.DataFrame,
        cashflow_statement: pd.DataFrame
    ) -> set:
        """获取三大报表都有数据的报告期"""
        
        # 获取日期列名
        date_col = self._get_date_column(balance_sheet)
        
        # 获取各报表的报告期
        balance_dates = set(balance_sheet[date_col].unique())
        income_dates = set(income_statement[date_col].unique())
        cashflow_dates = set(cashflow_statement[date_col].unique())
        
        # 取交集
        common_dates = balance_dates & income_dates & cashflow_dates
        
        return common_dates
    
    def _get_date_column(self, df: pd.DataFrame) -> str:
        """获取日期列名"""
        if '报告期' in df.columns:
            return '报告期'
        elif 'end_date' in df.columns:
            return 'end_date'
        else:
            raise ValueError("未找到日期列")
    
    def _filter_by_dates(self, df: pd.DataFrame, dates: set) -> pd.DataFrame:
        """按日期筛选数据"""
        date_col = self._get_date_column(df)
        return df[df[date_col].isin(dates)].copy()
    
    def _calculate_ttm_metric(self, df: pd.DataFrame, metric_col: str) -> Dict[str, float]:
        """
        计算TTM指标（通用方法）
        
        TTM = 今年Q累计 - 去年同Q累计 + 去年Q4累计
        
        Args:
            df: 财务报表数据
            metric_col: 指标列名（如'营业收入'、'营业成本'、'经营活动产生的现金流量净额'）
        
        Returns:
            {报告期: TTM值}
        """
        date_col = self._get_date_column(df)
        
        # 检查列是否存在
        if metric_col not in df.columns:
            return {}
        
        # 按日期排序
        df_sorted = df.sort_values(date_col).copy()
        
        ttm_values = {}
        
        for idx, row in df_sorted.iterrows():
            current_date = row[date_col]
            current_value = row[metric_col]
            
            # 跳过空值
            if pd.isna(current_value):
                continue
            
            # 解析日期
            year = int(str(current_date)[:4])
            month = int(str(current_date)[4:6])
            quarter = (month - 1) // 3 + 1
            
            # 如果是Q4，直接使用累计值作为TTM
            if quarter == 4:
                ttm_values[current_date] = current_value
                continue
            
            # 查找去年同期和去年Q4
            last_year = year - 1
            current_date_str = str(int(current_date))
            last_year_same_q = int(f"{last_year}{current_date_str[4:]}")
            last_year_q4 = int(f"{last_year}1231")
            
            # 获取去年同期数据
            last_year_same_q_data = df_sorted[df_sorted[date_col] == last_year_same_q]
            last_year_q4_data = df_sorted[df_sorted[date_col] == last_year_q4]
            
            if len(last_year_q4_data) > 0:
                last_year_q4_value = last_year_q4_data.iloc[0][metric_col]
                
                if pd.notna(last_year_q4_value):
                    # 计算TTM
                    if len(last_year_same_q_data) > 0:
                        last_year_same_q_value = last_year_same_q_data.iloc[0][metric_col]
                        if pd.notna(last_year_same_q_value):
                            ttm = current_value - last_year_same_q_value + last_year_q4_value
                        else:
                            # 如果去年同期为空，说明是Q1，直接用当期 + 去年Q4
                            ttm = current_value + last_year_q4_value
                    else:
                        # Q1的情况
                        ttm = current_value + last_year_q4_value
                    
                    ttm_values[current_date] = ttm
        
        return ttm_values
    
    def _use_current_values(self, data: pd.DataFrame, metric_col: str) -> Dict[str, float]:
        """
        直接使用当期值作为 TTM 值（用于已经是 TTM 格式的数据）
        
        Args:
            data: 财务数据
            metric_col: 指标列名
            
        Returns:
            {报告期: 当期值}
        """
        date_col = self._get_date_column(data)
        current_values = {}
        
        for _, row in data.iterrows():
            date = row[date_col]
            if isinstance(date, str):
                date = date.replace('-', '')
            date = str(int(date))
            
            value = row.get(metric_col)
            if pd.notna(value):
                current_values[date] = value
        
        return current_values
    
    def _calculate_ttm_revenue(self, income_statement: pd.DataFrame) -> Dict[str, float]:
        """
        计算TTM营业收入
        
        Returns:
            {报告期: TTM营业收入}
        """
        revenue_col = '营业收入' if '营业收入' in income_statement.columns else 'revenue'
        return self._calculate_ttm_metric(income_statement, revenue_col)
    
    def _calculate_indicators_for_date(
        self,
        date: str,
        balance_sheet: pd.DataFrame,
        income_statement: pd.DataFrame,
        cashflow_statement: pd.DataFrame,
        ttm_revenue: Dict[str, float],
        ttm_cost: Dict[str, float],
        ttm_ocf: Dict[str, float]
    ) -> Optional[Dict]:
        """计算指定日期的所有指标"""
        
        date_col = self._get_date_column(balance_sheet)
        
        # 获取当期数据
        balance_current = balance_sheet[balance_sheet[date_col] == date]
        income_current = income_statement[income_statement[date_col] == date]
        cashflow_current = cashflow_statement[cashflow_statement[date_col] == date]
        
        if len(balance_current) == 0 or len(income_current) == 0 or len(cashflow_current) == 0:
            return None
        
        balance_current = balance_current.iloc[0]
        income_current = income_current.iloc[0]
        cashflow_current = cashflow_current.iloc[0]
        
        # 获取去年同期数据（用于计算TTM指标的平均值）
        balance_last_year = self._get_last_year_same_period_data(balance_sheet, date)
        
        # 初始化结果
        result = {'报告期': date}
        
        # 1. 计算应收账款周转率对数和毛利率
        indicator1 = self._calculate_indicator1(
            balance_current, balance_last_year, income_current, 
            ttm_revenue.get(date), ttm_cost.get(date)
        )
        result.update(indicator1)
        
        # 2. 计算长期经营资产周转率对数
        indicator2 = self._calculate_indicator2(
            balance_current, balance_last_year, ttm_revenue.get(date)
        )
        result.update(indicator2)
        
        # 3. 计算净营运资本比率
        indicator3 = self._calculate_indicator3(balance_current)
        result.update(indicator3)
        
        # 4. 计算经营现金流比率
        indicator4 = self._calculate_indicator4(balance_current, cashflow_current, ttm_ocf.get(date))
        result.update(indicator4)
        
        return result
    
    def _get_last_period_data(
        self,
        df: pd.DataFrame,
        current_date: str
    ) -> Optional[pd.Series]:
        """获取上期数据（上一个季度）"""
        
        date_col = self._get_date_column(df)
        
        # 解析当前日期
        year = int(str(current_date)[:4])
        month = int(str(current_date)[4:6])
        
        # 计算上期日期
        if month == 3:
            last_date = f"{year-1}1231"
        elif month == 6:
            last_date = f"{year}0331"
        elif month == 9:
            last_date = f"{year}0630"
        else:  # 12月
            last_date = f"{year}0930"
        
        # 查找上期数据
        last_data = df[df[date_col] == last_date]
        
        if len(last_data) > 0:
            return last_data.iloc[0]
        else:
            return None
    
    def _get_last_year_same_period_data(
        self,
        df: pd.DataFrame,
        current_date: str
    ) -> Optional[pd.Series]:
        """获取去年同期数据（用于计算TTM指标的平均值）"""
        
        date_col = self._get_date_column(df)
        
        # 解析当前日期
        current_date_int = int(current_date)
        year = current_date_int // 10000
        month_day = current_date_int % 10000
        
        # 计算去年同期日期
        last_year_date = (year - 1) * 10000 + month_day
        
        # 查找去年同期数据
        last_year_data = df[df[date_col] == last_year_date]
        
        if len(last_year_data) > 0:
            return last_year_data.iloc[0]
        else:
            return None
    
    def _safe_get_value(self, row: pd.Series, *field_names) -> float:
        """安全获取字段值，尝试多个字段名"""
        for field in field_names:
            if field in row.index:
                value = row[field]
                if pd.notna(value):
                    return float(value)
        return np.nan
    
    def _calculate_indicator1(
        self,
        balance_current: pd.Series,
        balance_last_year: Optional[pd.Series],
        income_current: pd.Series,
        ttm_revenue: Optional[float],
        ttm_cost: Optional[float]
    ) -> Dict:
        """
        计算指标1：盈利能力与客户质量
        - 应收账款周转率对数
        - 毛利率
        
        注意：balance_last_year是去年同期数据，用于计算平均应收账款
        """
        result = {}
        
        # 获取应收账款
        ar_current = self._safe_get_value(balance_current, '应收账款', 'accounts_receiv')
        
        # 计算平均应收账款（使用去年同期的平均值，消除季节性波动）
        if balance_last_year is not None:
            ar_last_year = self._safe_get_value(balance_last_year, '应收账款', 'accounts_receiv')
            if pd.notna(ar_current) and pd.notna(ar_last_year):
                avg_ar = (ar_current + ar_last_year) / 2
            else:
                avg_ar = ar_current
        else:
            avg_ar = ar_current
        
        # 计算应收账款周转率对数
        if pd.notna(ttm_revenue) and pd.notna(avg_ar) and avg_ar > 0:
            ar_turnover = ttm_revenue / avg_ar
            result['应收账款周转率'] = ar_turnover
            result['应收账款周转率对数'] = np.log(ar_turnover) if ar_turnover > 0 else np.nan
        else:
            result['应收账款周转率'] = np.nan
            result['应收账款周转率对数'] = np.nan
        
        # 计算毛利率（使用TTM数据）
        if pd.notna(ttm_revenue) and pd.notna(ttm_cost) and ttm_revenue != 0:
            gross_margin = (ttm_revenue - ttm_cost) / ttm_revenue * 100
            result['毛利率'] = gross_margin
        else:
            result['毛利率'] = np.nan
        
        return result
    
    def _calculate_indicator2(
        self,
        balance_current: pd.Series,
        balance_last_year: Optional[pd.Series],
        ttm_revenue: Optional[float]
    ) -> Dict:
        """
        计算指标2：再投资质量暨跑冒滴漏风险检验
        - 长期经营资产周转率对数
        
        长期经营资产 = 固定资产 + 在建工程 + 生产性生物资产 + 公益性生物资产 
                    + 油气资产 + 使用权资产 + 无形资产 + 开发支出 
                    + 商誉 + 长期待摊费用 + 其他非流动资产
        
        注意：balance_last_year是去年同期数据，用于计算平均长期资产
        """
        result = {}
        
        # 计算长期经营资产
        def get_long_term_assets(row: pd.Series) -> float:
            fields = [
                ('固定资产', 'fix_assets'),
                ('在建工程', 'cip'),
                ('生产性生物资产', 'produc_bio_assets'),
                ('油气资产', 'oil_and_gas_assets'),
                ('使用权资产', 'use_right_assets'),
                ('无形资产', 'intan_assets'),
                ('开发支出', 'r_and_d'),
                ('商誉', 'goodwill'),
                ('长期待摊费用', 'lt_amor_exp'),
                ('其他非流动资产', 'oth_nca')
            ]
            
            total = 0
            for cn_name, en_name in fields:
                value = self._safe_get_value(row, cn_name, en_name)
                if pd.notna(value):
                    total += value
            
            return total if total > 0 else np.nan
        
        lta_current = get_long_term_assets(balance_current)
        
        # 计算平均长期经营资产（使用去年同期的平均值，消除季节性波动）
        if balance_last_year is not None:
            lta_last_year = get_long_term_assets(balance_last_year)
            if pd.notna(lta_current) and pd.notna(lta_last_year):
                avg_lta = (lta_current + lta_last_year) / 2
            else:
                avg_lta = lta_current
        else:
            avg_lta = lta_current
        
        # 计算长期经营资产周转率对数
        if pd.notna(ttm_revenue) and pd.notna(avg_lta) and avg_lta > 0:
            lta_turnover = ttm_revenue / avg_lta
            result['长期经营资产周转率'] = lta_turnover
            result['长期经营资产周转率对数'] = np.log(lta_turnover) if lta_turnover > 0 else np.nan
        else:
            result['长期经营资产周转率'] = np.nan
            result['长期经营资产周转率对数'] = np.nan
        
        return result
    
    def _calculate_indicator3(self, balance_current: pd.Series) -> Dict:
        """
        计算指标3：产业链地位检验暨资金运用能力
        - 净营运资本比率
        
        净营运资本 = 应收账款 + 应收票据 + 应收款项融资 + 合同资产 
                  - 应付账款 - 应付票据 - 合同负债
        """
        result = {}
        
        # 应收项目
        ar = self._safe_get_value(balance_current, '应收账款', 'accounts_receiv')
        notes_receiv = self._safe_get_value(balance_current, '应收票据', 'notes_receiv')
        receiv_financing = self._safe_get_value(balance_current, '应收款项融资', 'receiv_financing')
        contract_assets = self._safe_get_value(balance_current, '合同资产', 'contract_assets')
        
        # 应付项目
        ap = self._safe_get_value(balance_current, '应付账款', 'acct_payable', 'accounts_pay')
        notes_payable = self._safe_get_value(balance_current, '应付票据', 'notes_payable')
        contract_liab = self._safe_get_value(balance_current, '合同负债', 'contract_liab')
        
        # 计算净营运资本
        receivables = sum([x for x in [ar, notes_receiv, receiv_financing, contract_assets] if pd.notna(x)])
        payables = sum([x for x in [ap, notes_payable, contract_liab] if pd.notna(x)])
        
        net_working_capital = receivables - payables
        
        # 获取资产总额
        total_assets = self._safe_get_value(balance_current, '资产总计', 'total_assets')
        
        # 计算净营运资本比率
        if pd.notna(total_assets) and total_assets > 0:
            nwc_ratio = net_working_capital / total_assets * 100
            result['净营运资本'] = net_working_capital
            result['净营运资本比率'] = nwc_ratio
        else:
            result['净营运资本'] = np.nan
            result['净营运资本比率'] = np.nan
        
        return result
    
    def _calculate_indicator4(
        self,
        balance_current: pd.Series,
        cashflow_current: pd.Series,
        ttm_ocf: Optional[float]
    ) -> Dict:
        """
        计算指标4：真实盈利水平暨现金流创造能力
        - 经营现金流比率（使用TTM数据）
        """
        result = {}
        
        # 获取资产总额
        total_assets = self._safe_get_value(balance_current, '资产总计', 'total_assets')
        
        # 计算经营现金流比率（使用TTM数据）
        if pd.notna(ttm_ocf) and pd.notna(total_assets) and total_assets > 0:
            ocf_ratio = ttm_ocf / total_assets * 100
            result['经营活动现金流量净额'] = ttm_ocf
            result['经营现金流比率'] = ocf_ratio
        else:
            result['经营活动现金流量净额'] = np.nan
            result['经营现金流比率'] = np.nan
        
        return result
