"""
重命名验证测试：确保重命名后代码能正常工作
（此文件已过时，对应旧模块名 market_data_manager / market_analyzer / update_market_data，
 这些模块已被重命名。新验证见 test_financial_data_rename.py）
"""
import pytest
import os
import sys

pytestmark = pytest.mark.skip(reason="旧模块名已移除，验证逻辑已迁移至 test_financial_data_rename.py")

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestImports:
    """测试所有模块能正常导入"""
    
    def test_import_market_data_manager(self):
        """测试导入 MarketDataManager"""
        from market_data_manager import MarketDataManager
        assert MarketDataManager is not None
    
    def test_import_market_analyzer(self):
        """测试导入 MarketAnalyzer"""
        from market_analyzer import MarketAnalyzer
        assert MarketAnalyzer is not None
    
    def test_import_core_indicators_analyzer(self):
        """测试导入 CoreIndicatorsAnalyzer"""
        from core_indicators_analyzer import CoreIndicatorsAnalyzer
        assert CoreIndicatorsAnalyzer is not None
    
    def test_import_update_market_data(self):
        """测试导入 update_market_data 模块"""
        import update_market_data
        assert hasattr(update_market_data, 'MarketDataUpdater')


class TestDatabasePath:
    """测试数据库路径配置"""
    
    def test_market_data_manager_default_path(self):
        """测试 MarketDataManager 默认数据库路径"""
        from market_data_manager import MarketDataManager
        import inspect
        
        # 获取 __init__ 方法的签名
        sig = inspect.signature(MarketDataManager.__init__)
        db_path_param = sig.parameters.get('db_path')
        
        assert db_path_param is not None
        # 检查默认值包含 market_data.db
        assert 'market_data.db' in str(db_path_param.default)
    
    def test_update_market_data_default_path(self):
        """测试 MarketDataUpdater 默认数据库路径"""
        from update_market_data import MarketDataUpdater
        import inspect
        
        sig = inspect.signature(MarketDataUpdater.__init__)
        db_path_param = sig.parameters.get('db_path')
        
        assert db_path_param is not None
        assert 'market_data.db' in str(db_path_param.default)


class TestClassNames:
    """测试类名"""
    
    def test_market_data_manager_class_exists(self):
        """测试 MarketDataManager 类存在"""
        from market_data_manager import MarketDataManager
        assert MarketDataManager.__name__ == 'MarketDataManager'
    
    def test_market_analyzer_class_exists(self):
        """测试 MarketAnalyzer 类存在"""
        from market_analyzer import MarketAnalyzer
        assert MarketAnalyzer.__name__ == 'MarketAnalyzer'
    
    def test_market_data_updater_class_exists(self):
        """测试 MarketDataUpdater 类存在"""
        from update_market_data import MarketDataUpdater
        assert MarketDataUpdater.__name__ == 'MarketDataUpdater'


class TestBasicFunctionality:
    """测试基本功能（不依赖实际数据库）"""
    
    def test_market_data_manager_instantiation(self):
        """测试 MarketDataManager 能实例化"""
        from market_data_manager import MarketDataManager
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            manager = MarketDataManager(db_path)
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
