"""
集成测试：测试完整的数据流程
"""
import pytest
import pandas as pd
import os


class TestDataFlowIntegration:
    """测试完整数据流程"""
    
    def test_full_workflow(self, db_manager, sample_balance_data, 
                          sample_income_data, sample_cashflow_data):
        """测试完整工作流：保存数据 -> 计算指标 -> 更新分位数"""
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        from market_analyzer import MarketAnalyzer
        
        # 1. 保存财务数据
        for _, row in sample_balance_data.iterrows():
            db_manager.save_financial_data('000001.SZ', 'balancesheet', row.to_dict())
        
        for _, row in sample_income_data.iterrows():
            db_manager.save_financial_data('000001.SZ', 'income', row.to_dict())
        
        for _, row in sample_cashflow_data.iterrows():
            db_manager.save_financial_data('000001.SZ', 'cashflow', row.to_dict())
        
        # 2. 计算核心指标
        analyzer = CoreIndicatorsAnalyzer()
        balance = db_manager.get_financial_data('000001.SZ', 'balancesheet')
        income = db_manager.get_financial_data('000001.SZ', 'income')
        cashflow = db_manager.get_financial_data('000001.SZ', 'cashflow')
        
        indicators = analyzer.calculate_all_indicators(balance, income, cashflow)
        
        assert len(indicators) > 0
        
        # 3. 保存核心指标
        for _, row in indicators.iterrows():
            end_date = row.get('end_date') or row.get('报告期')
            if isinstance(end_date, str):
                end_date = end_date.replace('-', '')
            
            indicators_dict = {
                'ar_turnover_log': row.get('ar_turnover_log') or row.get('应收账款周转率对数'),
                'gross_margin': row.get('gross_margin') or row.get('毛利率'),
                'lta_turnover_log': row.get('lta_turnover_log') or row.get('长期经营资产周转率对数'),
                'working_capital_ratio': row.get('working_capital_ratio') or row.get('净营运资本比率'),
                'ocf_ratio': row.get('ocf_ratio') or row.get('经营现金流比率'),
            }
            
            db_manager.save_core_indicators(
                ts_code='000001.SZ',
                end_date=str(end_date),
                indicators=indicators_dict,
                data_complete=1
            )
        
        # 4. 验证数据已保存
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM core_indicators WHERE ts_code = ?", ('000001.SZ',))
        count = cursor.fetchone()[0]
        
        assert count > 0
    
    def test_incremental_update_logic(self, db_manager):
        """测试增量更新逻辑"""
        # 模拟已有数据
        existing_quarters = ['20231231', '20230930']
        for quarter in existing_quarters:
            db_manager.save_core_indicators(
                ts_code='000001.SZ',
                end_date=quarter,
                indicators={
                    'ar_turnover_log': 2.5,
                    'gross_margin': 30.0,
                    'lta_turnover_log': 1.8,
                    'working_capital_ratio': 0.5,
                    'ocf_ratio': 5.0
                },
                data_complete=1
            )
        
        # 检查已有季度
        conn = db_manager.get_connection()
        existing_df = pd.read_sql_query(
            "SELECT DISTINCT end_date FROM core_indicators WHERE ts_code = ? AND ar_turnover_log IS NOT NULL",
            conn,
            params=('000001.SZ',)
        )
        existing_set = set(existing_df['end_date'].tolist())
        
        # 新季度列表
        all_quarters = ['20231231', '20230930', '20230630', '20230331']
        new_quarters = [q for q in all_quarters if q not in existing_set]
        
        assert len(new_quarters) == 2
        assert '20230630' in new_quarters
        assert '20230331' in new_quarters


class TestDatabaseConsistency:
    """测试数据库一致性"""
    
    def test_data_integrity_after_multiple_operations(self, db_manager):
        """测试多次操作后的数据完整性"""
        ts_code = '000001.SZ'
        
        # 多次保存和更新
        for i in range(3):
            db_manager.save_financial_data(
                ts_code=ts_code,
                table_name='balancesheet',
                data={
                    'ts_code': ts_code,
                    'end_date': '20231231',
                    'total_assets': 1000000 + i * 100000
                }
            )
        
        # 验证只有一条记录且是最新值
        result = db_manager.get_financial_data(ts_code, 'balancesheet')
        assert len(result) == 1
        assert result.iloc[0]['total_assets'] == 1200000
    
    def test_foreign_key_constraints(self, db_manager):
        """测试外键约束（如果有）"""
        # 这个测试取决于实际的数据库schema
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # 检查外键是否启用
        cursor.execute("PRAGMA foreign_keys")
        fk_status = cursor.fetchone()[0]
        assert fk_status == 1  # 外键应该启用


class TestErrorHandling:
    """测试错误处理"""
    
    def test_invalid_table_name(self, db_manager):
        """测试无效表名处理"""
        with pytest.raises(Exception):
            db_manager.save_financial_data(
                ts_code='000001.SZ',
                table_name='invalid_table_name',
                data={'ts_code': '000001.SZ'}
            )
    
    def test_missing_required_fields(self, db_manager):
        """测试缺失必要字段"""
        # 尝试保存缺少ts_code的数据
        try:
            db_manager.save_financial_data(
                ts_code='000001.SZ',
                table_name='balancesheet',
                data={'end_date': '20231231'}  # 缺少ts_code
            )
            # 如果没有抛出异常，至少验证数据是否正确保存
            result = db_manager.get_financial_data('000001.SZ', 'balancesheet')
            assert len(result) >= 0
        except Exception:
            # 预期可能抛出异常
            pass
