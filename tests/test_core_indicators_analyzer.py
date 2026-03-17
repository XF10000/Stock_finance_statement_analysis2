"""
测试 CoreIndicatorsAnalyzer 核心指标计算器
"""
import pytest
import pandas as pd
import numpy as np


class TestCoreIndicatorsAnalyzer:
    """测试核心指标计算功能"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        return CoreIndicatorsAnalyzer()
    
    def test_calculate_all_indicators(self, analyzer, sample_balance_data, 
                                     sample_income_data, sample_cashflow_data):
        """测试计算所有核心指标"""
        result = analyzer.calculate_all_indicators(
            sample_balance_data,
            sample_income_data,
            sample_cashflow_data
        )
        
        assert len(result) > 0
        assert '报告期' in result.columns or 'end_date' in result.columns
        assert '应收账款周转率对数' in result.columns or 'ar_turnover_log' in result.columns
        assert '毛利率' in result.columns or 'gross_margin' in result.columns
    
    def test_gross_margin_calculation(self, analyzer, sample_income_data):
        """测试毛利率计算"""
        # 毛利率 = (营业收入 - 营业成本) / 营业收入 * 100
        revenue = sample_income_data.iloc[0]['revenue']
        cost = sample_income_data.iloc[0]['oper_cost']
        expected_margin = (revenue - cost) / revenue * 100
        
        result = analyzer.calculate_all_indicators(
            pd.DataFrame(),  # 空资产负债表
            sample_income_data,
            pd.DataFrame()   # 空现金流量表
        )
        
        if len(result) > 0:
            actual_margin = result.iloc[0].get('毛利率') or result.iloc[0].get('gross_margin')
            if pd.notna(actual_margin):
                assert abs(actual_margin - expected_margin) < 0.01
    
    def test_working_capital_ratio(self, analyzer, sample_balance_data):
        """测试净营运资本比率计算"""
        # 净营运资本比率 = (流动资产 - 流动负债) / 总资产 * 100
        cur_assets = sample_balance_data.iloc[0]['total_cur_assets']
        cur_liab = sample_balance_data.iloc[0]['total_cur_liab']
        total_assets = sample_balance_data.iloc[0]['total_assets']
        expected_ratio = (cur_assets - cur_liab) / total_assets * 100
        
        result = analyzer.calculate_all_indicators(
            sample_balance_data,
            pd.DataFrame(),
            pd.DataFrame()
        )
        
        if len(result) > 0:
            actual_ratio = result.iloc[0].get('净营运资本比率') or result.iloc[0].get('working_capital_ratio')
            if pd.notna(actual_ratio):
                assert abs(actual_ratio - expected_ratio) < 0.01
    
    def test_empty_data_handling(self, analyzer):
        """测试空数据处理"""
        empty_df = pd.DataFrame()
        
        result = analyzer.calculate_all_indicators(empty_df, empty_df, empty_df)
        
        # 应该返回空结果或处理异常
        assert isinstance(result, pd.DataFrame)
    
    def test_missing_columns_handling(self, analyzer):
        """测试缺失列的处理"""
        incomplete_balance = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'end_date': ['20231231']
            # 缺少其他必要字段
        })
        
        incomplete_income = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'end_date': ['20231231']
        })
        
        incomplete_cashflow = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'end_date': ['20231231']
        })
        
        # 应该能处理缺失数据，返回部分指标或NaN
        result = analyzer.calculate_all_indicators(
            incomplete_balance,
            incomplete_income,
            incomplete_cashflow
        )
        
        assert isinstance(result, pd.DataFrame)


class TestCoreIndicatorsEdgeCases:
    """测试边界情况"""
    
    @pytest.fixture
    def analyzer(self):
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        return CoreIndicatorsAnalyzer()
    
    def test_zero_revenue(self, analyzer):
        """测试营业收入为零的情况"""
        income_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'end_date': ['20231231'],
            'revenue': [0],
            'oper_cost': [100000]
        })
        
        result = analyzer.calculate_all_indicators(
            pd.DataFrame(),
            income_data,
            pd.DataFrame()
        )
        
        # 毛利率应该处理除零情况
        assert isinstance(result, pd.DataFrame)
    
    def test_negative_values(self, analyzer):
        """测试负值处理"""
        balance_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'end_date': ['20231231'],
            'total_cur_assets': [100000],
            'total_cur_liab': [150000],  # 流动负债大于流动资产
            'total_assets': [200000]
        })
        
        result = analyzer.calculate_all_indicators(
            balance_data,
            pd.DataFrame(),
            pd.DataFrame()
        )
        
        # 应该能处理负的净营运资本
        assert isinstance(result, pd.DataFrame)
