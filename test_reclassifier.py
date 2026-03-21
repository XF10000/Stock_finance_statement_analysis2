"""
资产负债表重分类功能单元测试
"""

import unittest
import pandas as pd
import yaml
import os
import tempfile
from balance_sheet_reclassifier import (
    load_company_rules,
    validate_reclassification_rule,
    reclassify_item,
    recalculate_subtotals,
    apply_reclassification,
    VALID_CATEGORIES
)


class TestReclassifier(unittest.TestCase):
    """重分类功能测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时配置文件
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml')
        self.config_path = self.temp_config.name
        
        # 创建测试用的DataFrame
        self.df_test = pd.DataFrame({
            '项目': ['金融资产合计', '其他非流动资产', '长期经营资产合计', '经营资产合计'],
            '20231231': [1000, 200, 800, 1000],
            '20241231': [1200, 300, 900, 1200]
        })
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
    
    def test_load_company_rules_empty(self):
        """测试加载空配置"""
        # 写入空配置
        with open(self.config_path, 'w') as f:
            yaml.dump({'company_rules': {}}, f)
        
        # 临时替换配置路径
        import balance_sheet_reclassifier
        original_path = 'config/company_specific_rules.yaml'
        balance_sheet_reclassifier.load_company_rules.__globals__['config_path'] = self.config_path
        
        rules = load_company_rules('603345.SH')
        self.assertEqual(rules, {})
    
    def test_validate_reclassification_rule_valid(self):
        """测试验证有效的重分类规则"""
        rule = {
            'from': '长期经营资产合计',
            'to': '金融资产合计',
            'percentage': 0.8,
            'reason': '测试'
        }
        
        available_items = ['其他非流动资产', '金融资产合计', '长期经营资产合计']
        
        is_valid, error_msg = validate_reclassification_rule(
            '其他非流动资产', rule, available_items
        )
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, '')
    
    def test_validate_reclassification_rule_missing_from(self):
        """测试缺少from字段的规则"""
        rule = {
            'to': '金融资产合计'
        }
        
        available_items = ['其他非流动资产']
        
        is_valid, error_msg = validate_reclassification_rule(
            '其他非流动资产', rule, available_items
        )
        
        self.assertFalse(is_valid)
        self.assertIn('from', error_msg)
    
    def test_validate_reclassification_rule_invalid_category(self):
        """测试无效的分类名称"""
        rule = {
            'from': '无效分类',
            'to': '金融资产合计'
        }
        
        available_items = ['其他非流动资产']
        
        is_valid, error_msg = validate_reclassification_rule(
            '其他非流动资产', rule, available_items
        )
        
        self.assertFalse(is_valid)
        self.assertIn('无效', error_msg)
    
    def test_validate_reclassification_rule_invalid_percentage(self):
        """测试无效的percentage值"""
        rule = {
            'from': '长期经营资产合计',
            'to': '金融资产合计',
            'percentage': 1.5  # 超出范围
        }
        
        available_items = ['其他非流动资产']
        
        is_valid, error_msg = validate_reclassification_rule(
            '其他非流动资产', rule, available_items
        )
        
        self.assertFalse(is_valid)
        self.assertIn('percentage', error_msg)
    
    def test_validate_reclassification_rule_item_not_exist(self):
        """测试科目不存在的情况"""
        rule = {
            'from': '长期经营资产合计',
            'to': '金融资产合计'
        }
        
        available_items = ['金融资产合计']  # 不包含其他非流动资产
        
        is_valid, error_msg = validate_reclassification_rule(
            '其他非流动资产', rule, available_items
        )
        
        self.assertFalse(is_valid)
        self.assertIn('不存在', error_msg)
    
    def test_reclassify_item_full(self):
        """测试完全重分类"""
        df = self.df_test.copy()
        
        df_result = reclassify_item(
            df, '其他非流动资产', '长期经营资产合计', '金融资产合计', percentage=1.0
        )
        
        # 检查是否添加了重分类标记
        self.assertIn('_reclassified_to', df_result.columns)
        
        # 检查科目是否被标记
        item_row = df_result[df_result['项目'] == '其他非流动资产']
        self.assertEqual(len(item_row), 1)
        self.assertEqual(item_row['_reclassified_to'].values[0], '金融资产合计')
    
    def test_reclassify_item_partial(self):
        """测试部分重分类"""
        df = self.df_test.copy()
        
        df_result = reclassify_item(
            df, '其他非流动资产', '长期经营资产合计', '金融资产合计', percentage=0.8
        )
        
        # 检查原科目金额是否调整为20%
        item_row = df_result[df_result['项目'] == '其他非流动资产']
        self.assertEqual(len(item_row), 1)
        self.assertAlmostEqual(item_row['20231231'].values[0], 200 * 0.2, places=2)
        
        # 检查是否创建了新的重分类部分
        new_item_row = df_result[df_result['项目'] == '其他非流动资产(重分类部分)']
        self.assertEqual(len(new_item_row), 1)
        self.assertAlmostEqual(new_item_row['20231231'].values[0], 200 * 0.8, places=2)
    
    def test_valid_categories(self):
        """测试有效分类列表"""
        # 检查关键分类是否存在
        self.assertIn('金融资产合计', VALID_CATEGORIES)
        self.assertIn('长期经营资产合计', VALID_CATEGORIES)
        self.assertIn('营运资产小计', VALID_CATEGORIES)
        self.assertIn('有息债务合计', VALID_CATEGORIES)
        self.assertIn('所有者权益合计', VALID_CATEGORIES)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建更完整的测试DataFrame
        self.df_test = pd.DataFrame({
            '项目': [
                '金融资产合计',
                '货币资金',
                '交易性金融资产',
                '长期股权投资',
                '经营资产合计',
                '周转性经营投入合计',
                '营运资产小计',
                '应收账款',
                '存货',
                '营运负债小计',
                '应付账款',
                '长期经营资产合计',
                '固定资产',
                '其他非流动资产',
                '有息债务合计',
                '所有者权益合计'
            ],
            '20231231': [
                5000,  # 金融资产合计
                3000,  # 货币资金
                2000,  # 交易性金融资产
                500,   # 长期股权投资
                4500,  # 经营资产合计
                1500,  # 周转性经营投入合计
                3000,  # 营运资产小计
                1500,  # 应收账款
                1500,  # 存货
                1500,  # 营运负债小计
                1500,  # 应付账款
                3000,  # 长期经营资产合计
                2500,  # 固定资产
                500,   # 其他非流动资产
                2000,  # 有息债务合计
                8000   # 所有者权益合计
            ]
        })
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 这个测试需要实际的配置文件和完整的重分类逻辑
        # 暂时跳过，等待完整实现
        pass


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
