#!/usr/bin/env python3
"""
TTM (Trailing Twelve Months) 财务数据生成器

功能：
1. 为任意季度生成 TTM 财务数据（合并过去4个季度）
2. 支持单只股票和批量股票
3. 返回标准的 DataFrame 格式，可直接用于核心指标计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging


class TTMGenerator:
    """TTM 财务数据生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_ttm_data(self, 
                         balance_data: pd.DataFrame,
                         income_data: pd.DataFrame,
                         cashflow_data: pd.DataFrame,
                         target_quarter: str) -> Dict[str, pd.DataFrame]:
        """
        为指定季度生成 TTM 财务数据
        
        Args:
            balance_data: 资产负债表数据（包含多个季度）
            income_data: 利润表数据（包含多个季度）
            cashflow_data: 现金流量表数据（包含多个季度）
            target_quarter: 目标季度（如 20250930）
            
        Returns:
            包含 TTM 数据的字典 {'balance': df, 'income': df, 'cashflow': df}
        """
        # 确定日期列名
        date_col = '报告期' if '报告期' in balance_data.columns else 'end_date'
        
        # 获取目标季度及之前的4个季度
        quarters = self._get_past_quarters(balance_data, target_quarter, date_col)
        
        if len(quarters) < 4:
            self.logger.warning(f"季度 {target_quarter} 的历史数据不足4个季度，无法生成 TTM")
            return None
        
        # 生成 TTM 数据
        ttm_balance = self._generate_ttm_balance(balance_data, target_quarter, date_col)
        ttm_income = self._generate_ttm_income(income_data, quarters, date_col)
        ttm_cashflow = self._generate_ttm_cashflow(cashflow_data, quarters, date_col)
        
        return {
            'balance': ttm_balance,
            'income': ttm_income,
            'cashflow': ttm_cashflow
        }
    
    def _get_past_quarters(self, data: pd.DataFrame, target_quarter: str, date_col: str) -> List[str]:
        """获取目标季度及之前的4个季度"""
        # 获取所有季度并排序
        all_quarters = sorted([str(q).replace('-', '') for q in data[date_col].unique()])
        
        # 找到目标季度的位置
        try:
            target_idx = all_quarters.index(target_quarter)
        except ValueError:
            self.logger.error(f"目标季度 {target_quarter} 不存在于数据中")
            return []
        
        # 获取过去4个季度（包括目标季度）
        if target_idx < 3:
            self.logger.warning(f"目标季度 {target_quarter} 之前的季度不足3个")
            return all_quarters[:target_idx + 1]
        
        return all_quarters[target_idx - 3:target_idx + 1]
    
    def _generate_ttm_balance(self, balance_data: pd.DataFrame, 
                             target_quarter: str, date_col: str) -> pd.DataFrame:
        """
        生成 TTM 资产负债表
        资产负债表是时点数据，直接取目标季度的数据
        """
        ttm_balance = balance_data[balance_data[date_col] == target_quarter].copy()
        
        if len(ttm_balance) == 0:
            self.logger.error(f"未找到季度 {target_quarter} 的资产负债表数据")
            return pd.DataFrame()
        
        return ttm_balance
    
    def _generate_ttm_income(self, income_data: pd.DataFrame,
                            quarters: List[str], date_col: str) -> pd.DataFrame:
        """
        生成 TTM 利润表
        利润表是累计数据，需要特殊处理：
        - 如果目标季度是 Q4，直接使用年报数据
        - 如果是 Q1/Q2/Q3，需要：当季累计 + (去年年报 - 去年同期累计)
        """
        target_quarter = quarters[-1]
        
        # 判断是否为年报（12月31日）
        if target_quarter.endswith('1231'):
            # 年报直接使用
            ttm_income = income_data[income_data[date_col] == target_quarter].copy()
        else:
            # 非年报需要计算
            ttm_income = self._calculate_ttm_income(income_data, quarters, date_col)
        
        return ttm_income
    
    def _calculate_ttm_income(self, income_data: pd.DataFrame,
                             quarters: List[str], date_col: str) -> pd.DataFrame:
        """
        计算非年报季度的 TTM 利润表
        公式：当季累计 + (去年年报 - 去年同期累计)
        """
        target_quarter = quarters[-1]
        
        # 获取当季数据
        current_data = income_data[income_data[date_col] == target_quarter]
        if len(current_data) == 0:
            return pd.DataFrame()
        
        current_data = current_data.iloc[0].copy()
        
        # 确定去年年报和去年同期
        year = int(target_quarter[:4])
        month_day = target_quarter[4:]
        
        last_year_annual = f"{year - 1}1231"
        last_year_same_quarter = f"{year - 1}{month_day}"
        
        # 获取去年年报数据
        last_annual_data = income_data[income_data[date_col] == last_year_annual]
        if len(last_annual_data) == 0:
            self.logger.warning(f"未找到去年年报 {last_year_annual}，无法计算 TTM")
            return pd.DataFrame()
        last_annual_data = last_annual_data.iloc[0]
        
        # 获取去年同期数据
        last_same_data = income_data[income_data[date_col] == last_year_same_quarter]
        if len(last_same_data) == 0:
            self.logger.warning(f"未找到去年同期 {last_year_same_quarter}，无法计算 TTM")
            return pd.DataFrame()
        last_same_data = last_same_data.iloc[0]
        
        # 计算 TTM：当季累计 + (去年年报 - 去年同期)
        ttm_data = current_data.copy()
        
        # 需要累计的字段（数值型字段）
        for col in current_data.index:
            if isinstance(current_data[col], (int, float, np.number)):
                if col in last_annual_data.index and col in last_same_data.index:
                    current_val = current_data[col] if pd.notna(current_data[col]) else 0
                    annual_val = last_annual_data[col] if pd.notna(last_annual_data[col]) else 0
                    same_val = last_same_data[col] if pd.notna(last_same_data[col]) else 0
                    
                    ttm_data[col] = current_val + (annual_val - same_val)
        
        return pd.DataFrame([ttm_data])
    
    def _generate_ttm_cashflow(self, cashflow_data: pd.DataFrame,
                              quarters: List[str], date_col: str) -> pd.DataFrame:
        """
        生成 TTM 现金流量表
        现金流量表是累计数据，处理方式与利润表相同
        """
        target_quarter = quarters[-1]
        
        # 判断是否为年报
        if target_quarter.endswith('1231'):
            ttm_cashflow = cashflow_data[cashflow_data[date_col] == target_quarter].copy()
        else:
            ttm_cashflow = self._calculate_ttm_cashflow(cashflow_data, quarters, date_col)
        
        return ttm_cashflow
    
    def _calculate_ttm_cashflow(self, cashflow_data: pd.DataFrame,
                               quarters: List[str], date_col: str) -> pd.DataFrame:
        """
        计算非年报季度的 TTM 现金流量表
        公式：当季累计 + (去年年报 - 去年同期累计)
        """
        target_quarter = quarters[-1]
        
        # 获取当季数据
        current_data = cashflow_data[cashflow_data[date_col] == target_quarter]
        if len(current_data) == 0:
            return pd.DataFrame()
        
        current_data = current_data.iloc[0].copy()
        
        # 确定去年年报和去年同期
        year = int(target_quarter[:4])
        month_day = target_quarter[4:]
        
        last_year_annual = f"{year - 1}1231"
        last_year_same_quarter = f"{year - 1}{month_day}"
        
        # 获取去年年报数据
        last_annual_data = cashflow_data[cashflow_data[date_col] == last_year_annual]
        if len(last_annual_data) == 0:
            self.logger.warning(f"未找到去年年报 {last_year_annual}，无法计算 TTM")
            return pd.DataFrame()
        last_annual_data = last_annual_data.iloc[0]
        
        # 获取去年同期数据
        last_same_data = cashflow_data[cashflow_data[date_col] == last_year_same_quarter]
        if len(last_same_data) == 0:
            self.logger.warning(f"未找到去年同期 {last_year_same_quarter}，无法计算 TTM")
            return pd.DataFrame()
        last_same_data = last_same_data.iloc[0]
        
        # 计算 TTM
        ttm_data = current_data.copy()
        
        for col in current_data.index:
            if isinstance(current_data[col], (int, float, np.number)):
                if col in last_annual_data.index and col in last_same_data.index:
                    current_val = current_data[col] if pd.notna(current_data[col]) else 0
                    annual_val = last_annual_data[col] if pd.notna(last_annual_data[col]) else 0
                    same_val = last_same_data[col] if pd.notna(last_same_data[col]) else 0
                    
                    ttm_data[col] = current_val + (annual_val - same_val)
        
        return pd.DataFrame([ttm_data])


if __name__ == '__main__':
    # 测试代码
    from financial_data_manager import FinancialDataManager
    
    logging.basicConfig(level=logging.INFO)
    
    db = FinancialDataManager('database/financial_data.db')
    generator = TTMGenerator()
    
    # 测试 000680 的 2024Q3 TTM
    ts_code = '000680.SZ'
    target_quarter = '20240930'
    
    balance = db.get_financial_data_batch_optimized([ts_code], 'balancesheet')
    income = db.get_financial_data_batch_optimized([ts_code], 'income')
    cashflow = db.get_financial_data_batch_optimized([ts_code], 'cashflow')
    
    # 列名统一化
    if 'TS股票代码' in balance.columns:
        balance = balance.rename(columns={'TS股票代码': 'ts_code'})
    if 'TS代码' in income.columns:
        income = income.rename(columns={'TS代码': 'ts_code'})
    if 'TS股票代码' in cashflow.columns:
        cashflow = cashflow.rename(columns={'TS股票代码': 'ts_code'})
    
    balance = balance[balance['ts_code'] == ts_code]
    income = income[income['ts_code'] == ts_code]
    cashflow = cashflow[cashflow['ts_code'] == ts_code]
    
    print(f"生成 {ts_code} 的 {target_quarter} TTM 数据...")
    ttm_data = generator.generate_ttm_data(balance, income, cashflow, target_quarter)
    
    if ttm_data:
        print(f"✓ TTM 数据生成成功")
        print(f"  Balance: {len(ttm_data['balance'])} 条")
        print(f"  Income: {len(ttm_data['income'])} 条")
        print(f"  Cashflow: {len(ttm_data['cashflow'])} 条")
        
        # 测试计算核心指标
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        analyzer = CoreIndicatorsAnalyzer()
        
        indicators = analyzer.calculate_all_indicators(
            ttm_data['balance'],
            ttm_data['income'],
            ttm_data['cashflow']
        )
        
        if len(indicators) > 0:
            print(f"\n✓ TTM 核心指标计算成功")
            row = indicators.iloc[0]
            print(f"  应收账款周转率对数: {row.get('应收账款周转率对数')}")
            print(f"  毛利率: {row.get('毛利率')}")
        else:
            print(f"\n⚠️  TTM 核心指标计算失败")
    else:
        print(f"⚠️  TTM 数据生成失败")
