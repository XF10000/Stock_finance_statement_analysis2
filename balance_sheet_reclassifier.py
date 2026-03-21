"""
资产负债表公司特定重分类模块

提供公司级别的科目重分类功能，允许用户为特定公司自定义科目分类规则。
"""

import os
import yaml
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple

# 配置日志
logger = logging.getLogger(__name__)


# 支持的分类层级定义
VALID_CATEGORIES = {
    # 资产侧
    '金融资产合计',
    '长期股权投资',
    '经营资产合计',
    '周转性经营投入合计',
    '长期经营资产合计',
    '营运资产小计',
    '营运负债小计',
    # 负债及权益侧
    '有息债务合计',
    '短期债务',
    '长期债务',
    '所有者权益合计',
    '归属于母公司股东权益合计',
    '少数股东权益',
}


def load_company_rules(ts_code: str) -> Dict:
    """
    加载公司特定的重分类规则
    
    Args:
        ts_code: 股票代码
        
    Returns:
        dict: 该公司的重分类规则，如果没有配置则返回空字典
    """
    config_path = 'config/company_specific_rules.yaml'
    
    # 如果配置文件不存在，返回空字典
    if not os.path.exists(config_path):
        logger.debug(f"配置文件不存在: {config_path}")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config or 'company_rules' not in config:
            logger.debug("配置文件中没有 company_rules 节点")
            return {}
        
        company_rules = config['company_rules'].get(ts_code, {})
        
        if company_rules:
            logger.info(f"为 {ts_code} 加载了重分类规则")
        
        return company_rules
        
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}


def validate_reclassification_rule(item_name: str, rule: Dict, 
                                   available_items: List[str]) -> Tuple[bool, str]:
    """
    验证重分类规则的有效性
    
    Args:
        item_name: 科目名称
        rule: 单个重分类规则
        available_items: 数据中可用的科目列表
        
    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    # 检查必需字段
    if 'from' not in rule:
        return False, f"科目 '{item_name}' 缺少 'from' 字段"
    
    if 'to' not in rule:
        return False, f"科目 '{item_name}' 缺少 'to' 字段"
    
    # 检查分类名称是否有效
    from_category = rule['from']
    to_category = rule['to']
    
    if from_category not in VALID_CATEGORIES:
        return False, (f"科目 '{item_name}' 的 'from' 分类 '{from_category}' 无效\n"
                      f"可用分类: {', '.join(sorted(VALID_CATEGORIES))}")
    
    if to_category not in VALID_CATEGORIES:
        return False, (f"科目 '{item_name}' 的 'to' 分类 '{to_category}' 无效\n"
                      f"可用分类: {', '.join(sorted(VALID_CATEGORIES))}")
    
    # 检查科目是否存在于数据中
    if item_name not in available_items:
        return False, (f"科目 '{item_name}' 在数据中不存在\n"
                      f"提示: 请检查科目名称是否正确")
    
    # 检查 percentage 字段（如果存在）
    if 'percentage' in rule:
        percentage = rule['percentage']
        if not isinstance(percentage, (int, float)):
            return False, f"科目 '{item_name}' 的 'percentage' 必须是数字"
        
        if not 0 < percentage <= 1:
            return False, f"科目 '{item_name}' 的 'percentage' 必须在 0 到 1 之间，当前值: {percentage}"
    
    return True, ""


def find_item_category(df: pd.DataFrame, item_name: str, 
                       expected_category: str) -> Tuple[bool, str]:
    """
    查找科目在DataFrame中的实际分类位置
    
    Args:
        df: 资产负债表DataFrame
        item_name: 科目名称
        expected_category: 期望的分类（from字段）
        
    Returns:
        Tuple[bool, str]: (是否在期望分类中, 实际分类名称)
    """
    # 这个函数的实现需要根据实际的DataFrame结构来确定
    # 暂时简化处理，假设科目就在指定的分类下
    # TODO: 实现更精确的分类查找逻辑
    return True, expected_category


def apply_reclassification(df: pd.DataFrame, ts_code: str) -> pd.DataFrame:
    """
    应用公司特定的重分类规则
    
    Args:
        df: 重构后的资产负债表DataFrame
        ts_code: 股票代码
        
    Returns:
        pd.DataFrame: 应用重分类后的DataFrame
    """
    # 加载规则
    rules = load_company_rules(ts_code)
    
    if not rules or 'reclassify' not in rules:
        logger.debug(f"{ts_code} 没有重分类规则")
        return df
    
    reclassify_rules = rules['reclassify']
    
    if not reclassify_rules:
        return df
    
    logger.info(f"正在为 {ts_code} 应用重分类规则...")
    
    # 获取数据中可用的科目列表
    available_items = df['项目'].tolist()
    
    # 验证所有规则
    for item_name, rule in reclassify_rules.items():
        is_valid, error_msg = validate_reclassification_rule(
            item_name, rule, available_items
        )
        
        if not is_valid:
            logger.error(f"重分类规则验证失败: {error_msg}")
            raise ValueError(error_msg)
    
    # 应用每个重分类规则
    reclassified_count = 0
    for item_name, rule in reclassify_rules.items():
        from_category = rule['from']
        to_category = rule['to']
        percentage = rule.get('percentage', 1.0)
        reason = rule.get('reason', '')
        
        # 执行重分类
        df = reclassify_item(
            df, item_name, from_category, to_category, percentage
        )
        
        # 记录日志
        logger.info(f"重分类: {item_name} ({percentage*100:.1f}%)")
        logger.info(f"  从: {from_category}")
        logger.info(f"  到: {to_category}")
        if reason:
            logger.info(f"  原因: {reason}")
        
        reclassified_count += 1
    
    # 重新计算小计和合计
    logger.info("重新计算小计和合计...")
    df = recalculate_subtotals(df)
    
    logger.info(f"重分类完成，共处理 {reclassified_count} 个科目")
    
    return df


def reclassify_item(df: pd.DataFrame, item_name: str, from_category: str,
                   to_category: str, percentage: float = 1.0) -> pd.DataFrame:
    """
    重分类单个科目
    
    Args:
        df: DataFrame
        item_name: 科目名称
        from_category: 原分类
        to_category: 目标分类
        percentage: 重分类比例（0-1之间）
        
    Returns:
        pd.DataFrame: 更新后的DataFrame
    """
    # 复制DataFrame以避免修改原始数据
    df = df.copy()
    
    # 获取科目所在的行索引
    item_idx = df[df['项目'] == item_name].index
    
    if len(item_idx) == 0:
        raise ValueError(f"科目 '{item_name}' 在数据中不存在")
    
    item_idx = item_idx[0]
    
    # 获取所有日期列（除了'项目'列）
    date_columns = [col for col in df.columns if col != '项目']
    
    if percentage == 1.0:
        # 完全重分类：直接移动科目
        # 从原分类中移除（通过标记实现）
        df.loc[item_idx, '_reclassified_from'] = from_category
        df.loc[item_idx, '_reclassified_to'] = to_category
        
    else:
        # 部分重分类：需要拆分科目
        # 1. 调整原科目的金额为 (1 - percentage)
        for col in date_columns:
            if pd.notna(df.loc[item_idx, col]):
                original_value = float(df.loc[item_idx, col])
                df.loc[item_idx, col] = original_value * (1 - percentage)
        
        # 2. 创建新的重分类部分
        new_row = df.loc[item_idx].copy()
        new_row['项目'] = f"{item_name}(重分类部分)"
        
        for col in date_columns:
            if pd.notna(df.loc[item_idx, col]):
                original_value = float(df.loc[item_idx, col]) / (1 - percentage)  # 恢复原值
                new_row[col] = original_value * percentage
        
        new_row['_reclassified_from'] = from_category
        new_row['_reclassified_to'] = to_category
        
        # 插入新行到DataFrame
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    return df


def recalculate_subtotals(df: pd.DataFrame) -> pd.DataFrame:
    """
    重新计算所有小计和合计项
    
    这个函数需要根据资产负债表的具体结构来实现
    目前先返回原DataFrame，后续需要实现完整的重新计算逻辑
    
    Args:
        df: DataFrame
        
    Returns:
        pd.DataFrame: 更新后的DataFrame
    """
    # TODO: 实现完整的小计和合计重新计算逻辑
    # 这需要知道每个小计/合计项包含哪些明细科目
    
    # 获取所有重分类的科目
    reclassified_items = df[df['_reclassified_to'].notna()] if '_reclassified_to' in df.columns else pd.DataFrame()
    
    if len(reclassified_items) == 0:
        return df
    
    # 获取日期列
    date_columns = [col for col in df.columns if col != '项目' and not col.startswith('_')]
    
    # 定义分类层级关系
    category_structure = {
        '金融资产合计': [],
        '长期经营资产合计': [],
        '营运资产小计': [],
        '营运负债小计': [],
        '周转性经营投入合计': ['营运资产小计', '营运负债小计'],
        '经营资产合计': ['周转性经营投入合计', '长期经营资产合计'],
        '短期债务': [],
        '长期债务': [],
        '有息债务合计': ['短期债务', '长期债务'],
        '归属于母公司股东权益合计': [],
        '少数股东权益': [],
        '所有者权益合计': ['归属于母公司股东权益合计', '少数股东权益'],
    }
    
    # 对于每个重分类的科目，更新相关的小计和合计
    for _, item_row in reclassified_items.iterrows():
        item_name = item_row['项目']
        from_cat = item_row['_reclassified_from']
        to_cat = item_row['_reclassified_to']
        
        # 从原分类中减去
        from_idx = df[df['项目'] == from_cat].index
        if len(from_idx) > 0:
            for col in date_columns:
                if pd.notna(item_row[col]) and pd.notna(df.loc[from_idx[0], col]):
                    df.loc[from_idx[0], col] = float(df.loc[from_idx[0], col]) - float(item_row[col])
        
        # 加到目标分类
        to_idx = df[df['项目'] == to_cat].index
        if len(to_idx) > 0:
            for col in date_columns:
                if pd.notna(item_row[col]):
                    current_val = df.loc[to_idx[0], col]
                    if pd.isna(current_val):
                        current_val = 0
                    df.loc[to_idx[0], col] = float(current_val) + float(item_row[col])
    
    # 清理临时标记列
    if '_reclassified_from' in df.columns:
        df = df.drop(columns=['_reclassified_from'])
    if '_reclassified_to' in df.columns:
        df = df.drop(columns=['_reclassified_to'])
    
    return df


def get_reclassification_summary(ts_code: str) -> str:
    """
    获取重分类规则的摘要信息
    
    Args:
        ts_code: 股票代码
        
    Returns:
        str: 摘要信息
    """
    rules = load_company_rules(ts_code)
    
    if not rules or 'reclassify' not in rules:
        return f"{ts_code}: 无重分类规则"
    
    reclassify_rules = rules['reclassify']
    count = len(reclassify_rules)
    
    summary = f"{ts_code}: {count} 个重分类规则\n"
    
    for item_name, rule in reclassify_rules.items():
        percentage = rule.get('percentage', 1.0)
        summary += f"  - {item_name}: {rule['from']} → {rule['to']} ({percentage*100:.0f}%)\n"
    
    return summary
