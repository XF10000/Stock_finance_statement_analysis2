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
    
    # 重新计算小计和合计（含级联更新父级合计）
    logger.info("重新计算小计和合计...")
    df = recalculate_subtotals(df)
    
    # 将重分类行物理移动到目标区段
    logger.info("调整行顺序：将重分类项目移至目标区段...")
    df = reorder_reclassified_items(df, reclassify_rules)
    
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
        # 确保日期列为 float，避免 int64 列写入浮点数报 TypeError
        for col in date_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)
        
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



# 当某个直接小计发生变化时，需要级联更新的父级合计
# 格式: {变化的直接小计: [需要同方向更新的父级合计列表]}
_CASCADE_PARENTS = {
    '长期经营资产合计':             ['经营资产合计'],
    '周转性经营投入合计':           ['经营资产合计'],
    '短期债务':                     ['有息债务合计', '资本总额'],
    '长期债务':                     ['有息债务合计', '资本总额'],
    '有息债务合计':                 ['资本总额'],
    '归属于母公司股东权益合计':     ['所有者权益合计', '资本总额'],
    '少数股东权益':                 ['所有者权益合计', '资本总额'],
    '所有者权益合计':               ['资本总额'],
}

# 重分类后，被移动项目应插入到目标区段的哪个"锚点行"之前
# 格式: {目标分类: 紧跟在目标区段之后的第一行（锚点）}
_SECTION_INSERT_BEFORE = {
    '金融资产合计':         '长期股权投资',
    '长期经营资产合计':     '资产总额',
    '营运资产小计':         '营运负债小计',
    '营运负债小计':         '长期经营资产合计',
    '周转性经营投入合计':   '长期经营资产合计',
    '短期债务':             '长期债务',
    '长期债务':             '所有者权益合计',
}


def _update_row(df: pd.DataFrame, row_name: str,
                date_columns: list, delta: pd.Series) -> None:
    """在DataFrame中找到指定行并加上delta（in-place）。"""
    idx_list = df[df['项目'] == row_name].index
    if len(idx_list) == 0:
        return
    idx = idx_list[0]
    for col in date_columns:
        d = delta.get(col)
        if d is None or pd.isna(d):
            continue
        cur = df.loc[idx, col]
        if pd.isna(cur):
            cur = 0.0
        df.loc[idx, col] = float(cur) + float(d)


def recalculate_subtotals(df: pd.DataFrame) -> pd.DataFrame:
    """
    重新计算所有小计和合计项（含级联更新父级合计）。
    
    Args:
        df: DataFrame
        
    Returns:
        pd.DataFrame: 更新后的DataFrame
    """
    # 获取所有重分类的科目
    reclassified_items = df[df['_reclassified_to'].notna()] if '_reclassified_to' in df.columns else pd.DataFrame()
    
    if len(reclassified_items) == 0:
        return df
    
    # 获取日期列
    date_columns = [col for col in df.columns if col != '项目' and not col.startswith('_')]
    
    for _, item_row in reclassified_items.iterrows():
        from_cat = item_row['_reclassified_from']
        to_cat   = item_row['_reclassified_to']
        
        # 提取该行的数值 delta（重分类金额）
        delta = pd.Series({col: item_row[col] for col in date_columns})
        neg_delta = -delta
        
        # ── 从原分类中减去（及其父级）
        _update_row(df, from_cat, date_columns, neg_delta)
        for parent in _CASCADE_PARENTS.get(from_cat, []):
            _update_row(df, parent, date_columns, neg_delta)
        
        # ── 加到目标分类（及其父级）
        _update_row(df, to_cat, date_columns, delta)
        for parent in _CASCADE_PARENTS.get(to_cat, []):
            _update_row(df, parent, date_columns, delta)
    
    # 清理临时标记列
    if '_reclassified_from' in df.columns:
        df = df.drop(columns=['_reclassified_from'])
    if '_reclassified_to' in df.columns:
        df = df.drop(columns=['_reclassified_to'])
    
    return df


def reorder_reclassified_items(df: pd.DataFrame,
                                reclassify_rules: dict) -> pd.DataFrame:
    """
    将被重分类的行物理移动到目标区段的末尾（紧接在锚点行之前）。
    
    Args:
        df: recalculate_subtotals 已处理完毕的 DataFrame
        reclassify_rules: 原始重分类规则字典 {item_name: {from, to, ...}}
        
    Returns:
        行顺序调整后的 DataFrame
    """
    df = df.reset_index(drop=True)
    
    for item_name, rule in reclassify_rules.items():
        to_cat = rule.get('to', '')
        anchor = _SECTION_INSERT_BEFORE.get(to_cat)
        if anchor is None:
            continue
        
        # 找到 item 行和 anchor 行的当前位置
        item_rows = df[df['项目'] == item_name]
        anchor_rows = df[df['项目'] == anchor]
        if len(item_rows) == 0 or len(anchor_rows) == 0:
            continue
        
        item_pos  = item_rows.index[0]
        anchor_pos = anchor_rows.index[0]
        
        if item_pos == anchor_pos - 1:
            continue  # 已经在正确位置
        
        # 提取并删除 item 行
        row_to_move = df.loc[[item_pos]].copy()
        df = df.drop(index=item_pos).reset_index(drop=True)
        
        # 重新找 anchor 位置（删除后可能偏移）
        anchor_rows_new = df[df['项目'] == anchor]
        if len(anchor_rows_new) == 0:
            continue
        new_anchor_pos = anchor_rows_new.index[0]
        
        # 插入到 anchor 之前
        df = pd.concat([
            df.iloc[:new_anchor_pos],
            row_to_move,
            df.iloc[new_anchor_pos:]
        ], ignore_index=True)
    
    return df


def recalculate_lta_after_reclassification(
    ts_code: str,
    balance_raw: pd.DataFrame,
    income_raw: pd.DataFrame,
    db_manager,
    balance_restructured: pd.DataFrame = None
) -> int:
    """
    重分类后重新计算 lta_turnover_log 并更新数据库及分位数排名。

    计算逻辑与 _calculate_indicator2 完全一致：手动汇总各明细字段，
    再加减被重分类进/出「长期经营资产」类别的科目金额。
    不使用「长期经营资产合计」小计，以避免引入递延所得税等差异项。

    处理范围（指标2 长期经营资产周转率对数）：
      - 原始 LTA 字段被移出 LTA：从汇总中减去                      ✓
      - 原始 LTA 字段被移入 LTA（已在原汇总中，无需操作）：        ✓
      - 非 LTA 字段被移入 LTA：从 balance_restructured 中读值加上  ✓（需传入）
      - 非 LTA 字段被移出 LTA（原汇总中本就没有，无需操作）：      ✓

    已知缺口（暂未处理，如需支持请按同样思路扩展）：
      - 影响指标3（营运净资本比率）的重分类，如将应收账款移至金融资产

    Args:
        ts_code: 股票代码
        balance_raw: 原始资产负债表（宽格式，行=日期，列=字段）
        income_raw: 原始利润表（宽格式，行=日期，列=字段）
        db_manager: FinancialDataManager 实例
        balance_restructured: 重构后资产负债表（长格式，行=项目，列=日期，可选）
                              当存在「非 LTA 字段移入 LTA」的规则时必须传入

    Returns:
        int: 更新的记录数
    """
    import numpy as np
    from datetime import datetime as _dt
    from core_indicators_analyzer import CoreIndicatorsAnalyzer

    rules = load_company_rules(ts_code)
    if not rules or not rules.get('reclassify'):
        return 0

    # _calculate_indicator2 使用的 LTA 字段（中文名 → 英文名）
    LTA_FIELDS = {
        '固定资产':       'fix_assets',
        '在建工程':       'cip',
        '生产性生物资产': 'produc_bio_assets',
        '公益性生物资产': 'public_welfare_bio_assets',
        '油气资产':       'oil_and_gas_assets',
        '使用权资产':     'use_right_assets',
        '无形资产':       'intan_assets',
        '开发支出':       'r_and_d',
        '商誉':           'goodwill',
        '长期待摊费用':   'lt_amor_exp',
        '其他非流动资产': 'oth_nca',
    }

    LTA_CATEGORIES = {'长期经营资产合计'}

    # 从 LTA 移出且属于原始 LTA 字段 → 需要减去
    items_to_subtract: dict = {}  # {cn_name: percentage}
    # 移入 LTA 且不在原始 LTA 字段中 → 需要加上（原汇总中本没有它）
    items_to_add: dict = {}       # {cn_name: percentage}

    for item_name, rule in rules['reclassify'].items():
        from_cat = rule.get('from', '')
        to_cat   = rule.get('to', '')
        pct = float(rule.get('percentage', 1.0))
        if from_cat in LTA_CATEGORIES and item_name in LTA_FIELDS:
            items_to_subtract[item_name] = pct
        if to_cat in LTA_CATEGORIES and item_name not in LTA_FIELDS:
            # 非 LTA 字段被移入 LTA，需要加入汇总
            items_to_add[item_name] = pct

    if not items_to_subtract and not items_to_add:
        logger.info(f"{ts_code}: 重分类规则不涉及 LTA 字段，无需重算 lta_turnover_log")
        return 0

    if items_to_add and balance_restructured is None:
        logger.warning(
            f"{ts_code}: 规则中有非 LTA 字段移入 LTA（{list(items_to_add)}），"
            f"需传入 balance_restructured 才能完整计算，该部分将被跳过"
        )

    analyzer = CoreIndicatorsAnalyzer()

    # 确定日期列
    date_col = '报告期' if '报告期' in balance_raw.columns else 'end_date'

    # 1. 逐期计算调整后的 LTA（原公式汇总 − 被重分类金额）
    lta_by_date: dict = {}
    for _, row in balance_raw.iterrows():
        raw_date = row[date_col]
        try:
            date_str = str(int(float(raw_date)))
        except (ValueError, TypeError):
            date_str = str(raw_date).replace('-', '')

        original_lta = 0.0
        for cn_name, en_name in LTA_FIELDS.items():
            val = analyzer._safe_get_value(row, cn_name, en_name)
            if pd.notna(val):
                original_lta += float(val)

        if original_lta <= 0:
            continue

        subtract = 0.0
        for item_name, pct in items_to_subtract.items():
            en_name = LTA_FIELDS[item_name]
            val = analyzer._safe_get_value(row, item_name, en_name)
            if pd.notna(val):
                subtract += float(val) * pct

        adjusted_lta = original_lta - subtract
        if adjusted_lta > 0:
            lta_by_date[date_str] = adjusted_lta

    if not lta_by_date:
        logger.warning(f"{ts_code}: 未计算出有效的调整后 LTA 数据")
        return 0

    # 1b. 加上「非 LTA 字段移入 LTA」的科目金额（从 balance_restructured 读取）
    if items_to_add and balance_restructured is not None:
        restr_date_cols = [c for c in balance_restructured.columns if c != '项目']
        for item_name, pct in items_to_add.items():
            item_rows = balance_restructured[balance_restructured['项目'] == item_name]
            if len(item_rows) == 0:
                logger.warning(f"{ts_code}: balance_restructured 中未找到 '{item_name}'，跳过 ADD")
                continue
            for col in restr_date_cols:
                try:
                    date_str = str(int(float(col)))
                except (ValueError, TypeError):
                    date_str = str(col).replace('-', '')
                if date_str not in lta_by_date:
                    continue
                val = item_rows.iloc[0].get(col)
                if pd.notna(val):
                    lta_by_date[date_str] += float(val) * pct
                    logger.debug(f"{ts_code} {date_str}: ADD {item_name} × {pct} = {float(val)*pct:.0f}")

    # 2. 计算 TTM 营业收入
    revenue_col = '营业收入' if '营业收入' in income_raw.columns else 'revenue'
    if revenue_col not in income_raw.columns:
        logger.warning(f"{ts_code}: 利润表中未找到营业收入字段")
        return 0

    ttm_revenue = analyzer._calculate_ttm_metric(income_raw, revenue_col)
    if not ttm_revenue:
        logger.warning(f"{ts_code}: 无法计算 TTM 营业收入")
        return 0

    # 3. 逐期计算新的 lta_turnover_log
    updated_values: dict = {}
    for raw_date, revenue in ttm_revenue.items():
        try:
            date_str = str(int(float(raw_date)))
        except (ValueError, TypeError):
            date_str = str(raw_date).replace('-', '')

        lta_current = lta_by_date.get(date_str)
        if lta_current is None:
            continue

        date_int = int(date_str)
        year, month_day = date_int // 10000, date_int % 10000
        last_year_date = str((year - 1) * 10000 + month_day)
        lta_last_year = lta_by_date.get(last_year_date)

        avg_lta = (lta_current + lta_last_year) / 2 if lta_last_year is not None else lta_current

        if avg_lta > 0 and revenue > 0:
            updated_values[date_str] = float(np.log(revenue / avg_lta))

    if not updated_values:
        logger.warning(f"{ts_code}: 没有可更新的 lta_turnover_log 数据")
        return 0

    # 4. 更新数据库
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    now_str = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
    updated_count = 0

    for date_str, lta_log in updated_values.items():
        cursor.execute(
            'UPDATE core_indicators SET lta_turnover_log = ?, update_time = ? '
            'WHERE ts_code = ? AND end_date = ?',
            (lta_log, now_str, ts_code, date_str)
        )
        updated_count += cursor.rowcount

    conn.commit()
    logger.info(f"{ts_code}: 更新了 {updated_count} 条 lta_turnover_log 记录")

    if updated_count == 0:
        return 0

    # 5. 对受影响的报告期重新计算分位数排名
    from financial_data_analyzer import FinancialDataAnalyzer
    fa = FinancialDataAnalyzer(db_manager)

    periods_done: set = set()
    for date_str in updated_values:
        if date_str in periods_done:
            continue
        is_ttm = not date_str.endswith('1231')
        try:
            fa.update_percentile_ranks(date_str, is_ttm=is_ttm)
            logger.info(f"{ts_code}: 已重算 {date_str} ({'TTM' if is_ttm else '年报'}) 分位数")
        except Exception as e:
            logger.warning(f"重算 {date_str} 分位数失败: {e}")
        periods_done.add(date_str)

    return updated_count


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
