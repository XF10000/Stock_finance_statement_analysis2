"""
重命名后的验证测试：确保所有新名称正确工作
"""
import pytest
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestNewImports:
    """测试新的模块名能正常导入"""
    
    def test_import_financial_data_manager(self):
        """测试导入 FinancialDataManager"""
        from financial_data_manager import FinancialDataManager
        assert FinancialDataManager is not None
    
    def test_import_financial_data_analyzer(self):
        """测试导入 FinancialDataAnalyzer"""
        from financial_data_analyzer import FinancialDataAnalyzer
        assert FinancialDataAnalyzer is not None
    
    def test_import_core_indicators_analyzer(self):
        """测试导入 CoreIndicatorsAnalyzer"""
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        assert CoreIndicatorsAnalyzer is not None
    
    def test_import_update_financial_data(self):
        """测试导入 update_financial_data 模块"""
        import update_financial_data
        assert hasattr(update_financial_data, 'FinancialDataUpdater')


class TestNewDatabasePath:
    """测试新的数据库路径配置"""
    
    def test_financial_data_manager_default_path(self):
        """测试 FinancialDataManager 默认数据库路径"""
        from financial_data_manager import FinancialDataManager
        import inspect
        
        # 获取 __init__ 方法的签名
        sig = inspect.signature(FinancialDataManager.__init__)
        db_path_param = sig.parameters.get('db_path')
        
        assert db_path_param is not None
        # 检查默认值包含 financial_data.db
        assert 'financial_data.db' in str(db_path_param.default)
    
    def test_update_financial_data_default_path(self):
        """测试 FinancialDataUpdater 默认数据库路径"""
        from update_financial_data import FinancialDataUpdater
        import inspect
        
        sig = inspect.signature(FinancialDataUpdater.__init__)
        db_path_param = sig.parameters.get('db_path')
        
        assert db_path_param is not None
        assert 'financial_data.db' in str(db_path_param.default)


class TestNewClassNames:
    """测试新的类名"""
    
    def test_financial_data_manager_class_exists(self):
        """测试 FinancialDataManager 类存在"""
        from financial_data_manager import FinancialDataManager
        assert FinancialDataManager.__name__ == 'FinancialDataManager'
    
    def test_financial_data_analyzer_class_exists(self):
        """测试 FinancialDataAnalyzer 类存在"""
        from financial_data_analyzer import FinancialDataAnalyzer
        assert FinancialDataAnalyzer.__name__ == 'FinancialDataAnalyzer'
    
    def test_financial_data_updater_class_exists(self):
        """测试 FinancialDataUpdater 类存在"""
        from update_financial_data import FinancialDataUpdater
        assert FinancialDataUpdater.__name__ == 'FinancialDataUpdater'


class TestOldNamesRemoved:
    """测试旧名称已被移除"""
    
    def test_market_data_manager_not_exists(self):
        """测试 market_data_manager 模块不存在"""
        with pytest.raises(ModuleNotFoundError):
            import market_data_manager
    
    def test_market_analyzer_not_exists(self):
        """测试 market_analyzer 模块不存在"""
        with pytest.raises(ModuleNotFoundError):
            import market_analyzer
    
    def test_update_market_data_not_exists(self):
        """测试 update_market_data 模块不存在"""
        with pytest.raises(ModuleNotFoundError):
            import update_market_data


class TestBasicFunctionality:
    """测试基本功能（不依赖实际数据库）"""
    
    def test_financial_data_manager_instantiation(self):
        """测试 FinancialDataManager 能实例化"""
        from financial_data_manager import FinancialDataManager
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            manager = FinancialDataManager(db_path)
            assert manager is not None
            assert manager.db_path == db_path
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_core_indicators_analyzer_instantiation(self):
        """测试 CoreIndicatorsAnalyzer 能实例化"""
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        
        analyzer = CoreIndicatorsAnalyzer()
        assert analyzer is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
