"""
测试 MarketAnalyzer 市场分析器
"""
import pytest
import pandas as pd


class TestMarketAnalyzer:
    """测试市场分析功能"""
    
    @pytest.fixture
    def analyzer(self, populated_db):
        """创建市场分析器实例"""
        from financial_data_analyzer import FinancialDataAnalyzer
        return FinancialDataAnalyzer(populated_db)
    
    def test_calculate_market_percentiles(self, analyzer, populated_db):
        """测试计算市场分位数"""
        # 先保存一些核心指标数据
        for i in range(10):
            populated_db.save_core_indicators(
                ts_code=f'00000{i}.SZ',
                end_date='20231231',
                indicators={
                    'ar_turnover_log': 2.0 + i * 0.1,
                    'gross_margin': 20.0 + i * 2.0,
                    'lta_turnover_log': 1.5 + i * 0.05,
                    'working_capital_ratio': 0.3 + i * 0.02,
                    'ocf_ratio': 4.0 + i * 0.5
                },
                data_complete=1
            )
        
        # 计算分位数
        result = analyzer.calculate_market_percentiles('20231231')
        
        assert isinstance(result, dict)
        assert 'ar_turnover_log' in result
        assert 'gross_margin' in result
        assert 'p50' in result['ar_turnover_log']  # 中位数
        assert 'mean' in result['ar_turnover_log']  # 均值
    
    def test_update_percentile_ranks(self, analyzer, populated_db):
        """测试更新分位数排名"""
        # 保存核心指标
        for i in range(5):
            populated_db.save_core_indicators(
                ts_code=f'00000{i}.SZ',
                end_date='20231231',
                indicators={
                    'ar_turnover_log': 2.0 + i * 0.5,
                    'gross_margin': 20.0 + i * 5.0,
                    'lta_turnover_log': 1.5,
                    'working_capital_ratio': 0.5,
                    'ocf_ratio': 5.0
                },
                data_complete=1
            )
        
        # 更新分位数排名
        count = analyzer.update_percentile_ranks('20231231')
        
        assert count == 5
        
        # 验证分位数已更新
        conn = populated_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ar_turnover_log_percentile, gross_margin_percentile
            FROM core_indicators
            WHERE ts_code = ? AND end_date = ?
        """, ('000000.SZ', '20231231'))
        
        row = cursor.fetchone()
        assert row is not None
        assert row[0] is not None  # 分位数应该已计算
        assert row[1] is not None
    
    def test_empty_quarter_handling(self, analyzer):
        """测试空季度数据处理"""
        result = analyzer.calculate_market_percentiles('20991231')
        
        # 应该返回空字典或处理异常
        assert isinstance(result, dict)
        assert len(result) == 0


class TestMarketAnalyzerStatistics:
    """测试统计计算"""
    
    @pytest.fixture
    def analyzer(self, populated_db):
        from financial_data_analyzer import FinancialDataAnalyzer
        return FinancialDataAnalyzer(populated_db)
    
    def test_percentile_calculation_accuracy(self, analyzer, populated_db):
        """测试分位数计算准确性"""
        # 创建已知分布的数据
        test_values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        
        for i, val in enumerate(test_values):
            populated_db.save_core_indicators(
                ts_code=f'00000{i}.SZ',
                end_date='20231231',
                indicators={
                    'ar_turnover_log': val,
                    'gross_margin': val * 10,
                    'lta_turnover_log': 1.0,
                    'working_capital_ratio': 0.5,
                    'ocf_ratio': 5.0
                },
                data_complete=1
            )
        
        result = analyzer.calculate_market_percentiles('20231231')
        
        # 中位数应该在5.5左右
        assert abs(result['ar_turnover_log']['p50'] - 5.5) < 0.1
        # 均值应该是5.5
        assert abs(result['ar_turnover_log']['mean'] - 5.5) < 0.1
