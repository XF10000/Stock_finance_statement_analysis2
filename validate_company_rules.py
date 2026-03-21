"""
公司特定重分类规则配置文件验证工具

用于验证 config/company_specific_rules.yaml 的格式和内容是否正确
"""

import os
import sys
import yaml
from balance_sheet_reclassifier import VALID_CATEGORIES


def validate_config_file():
    """验证配置文件"""
    config_path = 'config/company_specific_rules.yaml'
    
    print("=" * 60)
    print("公司特定重分类规则配置验证工具")
    print("=" * 60)
    print()
    
    # 检查文件是否存在
    if not os.path.exists(config_path):
        print(f"✗ 配置文件不存在: {config_path}")
        print(f"  提示: 请从 company_specific_rules.yaml.template 复制创建")
        return False
    
    print(f"✓ 配置文件存在: {config_path}")
    
    # 加载配置文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"✗ YAML格式错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 读取文件失败: {e}")
        return False
    
    print("✓ 配置文件格式正确")
    
    # 检查根节点
    if not config:
        print("✗ 配置文件为空")
        return False
    
    if 'company_rules' not in config:
        print("✗ 缺少 'company_rules' 根节点")
        return False
    
    company_rules = config['company_rules']
    
    if not company_rules:
        print("✓ 配置文件有效，但未配置任何公司规则")
        return True
    
    # 统计信息
    company_count = len(company_rules)
    total_rules = 0
    
    print(f"✓ 共配置 {company_count} 个公司")
    print()
    
    # 验证每个公司的规则
    all_valid = True
    
    for ts_code, rules in company_rules.items():
        print(f"验证公司: {ts_code}")
        
        if not rules:
            print(f"  ⚠ 该公司没有配置规则")
            continue
        
        if 'reclassify' not in rules:
            print(f"  ✗ 缺少 'reclassify' 节点")
            all_valid = False
            continue
        
        reclassify_rules = rules['reclassify']
        
        if not reclassify_rules:
            print(f"  ⚠ 'reclassify' 节点为空")
            continue
        
        rule_count = len(reclassify_rules)
        total_rules += rule_count
        print(f"  ✓ {rule_count} 个重分类规则")
        
        # 验证每个重分类规则
        for item_name, rule in reclassify_rules.items():
            is_valid, error_msg = validate_rule(ts_code, item_name, rule)
            
            if not is_valid:
                print(f"    ✗ {item_name}: {error_msg}")
                all_valid = False
            else:
                # 显示规则详情
                from_cat = rule['from']
                to_cat = rule['to']
                percentage = rule.get('percentage', 1.0)
                reason = rule.get('reason', '')
                
                print(f"    ✓ {item_name}")
                print(f"      从: {from_cat}")
                print(f"      到: {to_cat}")
                print(f"      比例: {percentage*100:.0f}%")
                if reason:
                    print(f"      原因: {reason}")
    
    print()
    print("=" * 60)
    
    if all_valid:
        print(f"✓ 验证通过！共 {company_count} 个公司，{total_rules} 个重分类规则")
        return True
    else:
        print(f"✗ 验证失败，请修正上述错误")
        return False


def validate_rule(ts_code: str, item_name: str, rule: dict) -> tuple:
    """
    验证单个重分类规则
    
    Returns:
        tuple: (是否有效, 错误信息)
    """
    # 检查必需字段
    if not isinstance(rule, dict):
        return False, "规则必须是字典格式"
    
    if 'from' not in rule:
        return False, "缺少 'from' 字段"
    
    if 'to' not in rule:
        return False, "缺少 'to' 字段"
    
    # 检查分类名称
    from_category = rule['from']
    to_category = rule['to']
    
    if from_category not in VALID_CATEGORIES:
        return False, f"'from' 分类 '{from_category}' 无效"
    
    if to_category not in VALID_CATEGORIES:
        return False, f"'to' 分类 '{to_category}' 无效"
    
    # 检查 percentage
    if 'percentage' in rule:
        percentage = rule['percentage']
        
        if not isinstance(percentage, (int, float)):
            return False, f"'percentage' 必须是数字，当前类型: {type(percentage)}"
        
        if not 0 < percentage <= 1:
            return False, f"'percentage' 必须在 0 到 1 之间，当前值: {percentage}"
    
    return True, ""


def print_valid_categories():
    """打印所有有效的分类名称"""
    print()
    print("=" * 60)
    print("有效的分类名称")
    print("=" * 60)
    print()
    
    print("资产侧:")
    print("  一级分类:")
    for cat in ['金融资产合计', '长期股权投资', '经营资产合计']:
        if cat in VALID_CATEGORIES:
            print(f"    - {cat}")
    
    print("  二级分类:")
    for cat in ['周转性经营投入合计', '长期经营资产合计']:
        if cat in VALID_CATEGORIES:
            print(f"    - {cat}")
    
    print("  三级分类:")
    for cat in ['营运资产小计', '营运负债小计']:
        if cat in VALID_CATEGORIES:
            print(f"    - {cat}")
    
    print()
    print("负债及权益侧:")
    print("  一级分类:")
    for cat in ['有息债务合计', '所有者权益合计']:
        if cat in VALID_CATEGORIES:
            print(f"    - {cat}")
    
    print("  二级分类:")
    for cat in ['短期债务', '长期债务', '归属于母公司股东权益合计', '少数股东权益']:
        if cat in VALID_CATEGORIES:
            print(f"    - {cat}")
    
    print()


if __name__ == '__main__':
    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--categories':
        print_valid_categories()
        sys.exit(0)
    
    # 验证配置文件
    success = validate_config_file()
    
    if not success:
        print()
        print("提示: 运行 'python validate_company_rules.py --categories' 查看所有有效的分类名称")
        sys.exit(1)
    
    sys.exit(0)
