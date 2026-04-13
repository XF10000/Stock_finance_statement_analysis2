"""
利润表重构模块
将传统利润表重构为股权价值增加表
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging


# ============================================================================
# 字段名映射（利润表）
# ============================================================================

INCOME_FIELD_MAPPING = {
    # 收入类
    '营业总收入': '营业总收入',
    '营业收入': '营业收入',
    'total_revenue': '营业收入',
    'revenue': '营业收入',
    
    # 成本类
    '营业总成本': '营业总成本',
    '营业成本': '营业成本',
    'total_cogs': '营业成本',
    'oper_cost': '营业成本',
    
    # 税金及附加
    '营业税金及附加': '税金及附加',
    'tax_surcharges': '税金及附加',
    
    # 期间费用
    '销售费用': '销售费用',
    'sell_exp': '销售费用',
    '管理费用': '管理费用',
    'admin_exp': '管理费用',
    '研发费用': '研发费用',
    'rd_exp': '研发费用',
    '财务费用': '财务费用',
    'fin_exp': '财务费用',
    
    # 财务费用明细
    '财务费用:利息费用': '利息费用',
    '财务费用：利息费用': '利息费用',
    '利息支出': '利息费用',
    'int_exp': '利息费用',
    '财务费用:利息收入': '利息收入(财务费用)',
    '财务费用：利息收入': '利息收入(财务费用)',
    
    # 资产减值
    '资产减值损失': '资产减值损失',
    'assets_impair_loss': '资产减值损失',
    '信用减值损失': '信用减值损失',
    'credit_impair_loss': '信用减值损失',
    
    # 其他经营相关
    '资产处置收益': '资产处置收益',
    'asset_dispose_income': '资产处置收益',
    '其他收益': '其他收益',
    'other_income': '其他收益',
    
    # 营业外收支
    '营业外收入': '营业外收入',
    'nonoper_income': '营业外收入',
    '营业外支出': '营业外支出',
    'nonoper_exp': '营业外支出',
    '非流动资产处置净损失': '非流动资产处置损失',
    
    # 投资收益
    '投资净收益': '投资收益',
    'invest_income': '投资收益',
    '投资收益': '投资收益',
    '对联营企业和合营企业的投资收益': '对联营企业投资收益',
    '对联营企业和合营企业投资收益': '对联营企业投资收益',
    '对联营企业和合营企业的投资': '对联营企业投资收益',
    '对联营企业投资收益': '对联营企业投资收益',
    'ass_invest_income': '对联营企业投资收益',
    
    # 金融资产收益相关
    '公允价值变动净收益': '公允价值变动收益',
    '公允价值变动收益': '公允价值变动收益',
    'fair_value_change_income': '公允价值变动收益',
    '汇兑净收益': '汇兑收益',
    '汇兑收益': '汇兑收益',
    'exchange_income': '汇兑收益',
    '净敞口套期收益': '净敞口套期收益',
    'net_open_hedging_income': '净敞口套期收益',
    
    # 利息收入（利润表中的）
    '利息收入': '利息收入',
    'int_income': '利息收入',
    
    # 其他综合收益
    '其他综合收益': '其他综合收益',
    'other_compre_income': '其他综合收益',
    
    # 所得税和利润
    '所得税费用': '所得税费用',
    'income_tax': '所得税费用',
    '利润总额': '利润总额',
    'profit_total': '利润总额',
    '净利润(含少数股东损益)': '净利润',
    '净利润(不含少数股东损益)': '净利润(归母)',
    '净利润': '净利润',
    'net_profit': '净利润',
    '少数股东损益': '少数股东损益',
    'minority_profit': '少数股东损益',
    
    # 其他
    '营业利润': '营业利润',
    'operate_profit': '营业利润',
}


# ============================================================================
# 利润表重构函数
# ============================================================================

def restructure_income_statement(df: pd.DataFrame, 
                                  equity_data: pd.DataFrame = None,
                                  equity_cost_rate: float = 0.08) -> pd.DataFrame:
    """
    重构利润表：将传统利润表转换为股权价值增加表
    
    Args:
        df: 转置后的利润表（行=报告期，列=项目）
        equity_data: 资产负债表重构数据（用于获取所有者权益合计）
        equity_cost_rate: 股权资本成本率，默认8%
        
    Returns:
        重构后的利润表（行=项目，列=报告期）
    """
    logger = logging.getLogger(__name__)
    logger.info("开始重构利润表...")
    
    # 确保所有列名都是字符串类型（避免整数列名导致的匹配失败）
    df = df.copy()
    df.columns = [str(col) for col in df.columns]
    
    # 如果有 equity_data，也确保其列名是字符串
    if equity_data is not None:
        equity_data = equity_data.copy()
        equity_data.columns = [str(col) for col in equity_data.columns]
    
    # 处理重复的列名（如 20250930, 20250930.1 等）
    df = _clean_duplicate_columns(df)
    
    # 确保数据格式正确
    if '字段名' in df.columns:
        # 已经是转置格式
        df_data = df.set_index('字段名')
        logger.info("输入数据为转置格式")
    elif '项目' in df.columns:
        # 已经是转置格式：项目名为第一列（从 main.py 传入）
        df_data = df.set_index('项目')
        logger.info("输入数据为转置格式（项目列）")
    elif '报告期' in df.columns or 'end_date' in df.columns:
        # 原始格式：需要转置
        logger.info("输入数据为原始格式，进行转置...")
        
        # 确定报告期列名
        date_col = '报告期' if '报告期' in df.columns else 'end_date'
        
        # 获取数值列（排除非数值列）
        non_numeric_cols = ['TS代码', 'ts_code', '公告日期', 'ann_date', '实际公告日期', 'f_ann_date',
                           '报告期', 'end_date', '报表类型', 'report_type', '公司类型', 'comp_type',
                           '报告期类型', 'end_type', '更新标识', 'update_flag']
        numeric_cols = [col for col in df.columns if col not in non_numeric_cols]
        
        # 提取数值部分和报告期
        df_work = df[[date_col] + numeric_cols].copy()
        
        # 设置报告期为索引，然后转置
        df_work = df_work.set_index(date_col)
        df_data = df_work.T
        
        # 重置索引
        df_data = df_data.reset_index()
        df_data = df_data.rename(columns={'index': '字段名'})
        df_data = df_data.set_index('字段名')
        
        logger.info(f"转置完成，数据形状: {df_data.shape}")
    else:
        logger.warning("无法识别数据格式，假设已经是正确格式")
        df_data = df.copy()
    
    # 标准化字段名
    df_data = _standardize_income_field_names(df_data)
    
    # 获取所有日期列
    date_columns = df_data.columns.tolist()
    
    # 创建重构后的数据结构
    restructured_data = {}
    
    # ========================================================================
    # 1. 营业收入与成本分析
    # ========================================================================
    logger.info("计算营业收入与成本...")
    
    revenue = _safe_get_value(df_data, '营业收入', date_columns)
    operating_cost = _safe_get_value(df_data, '营业成本', date_columns)
    
    restructured_data['营业收入'] = revenue
    restructured_data['营业成本'] = operating_cost
    
    # 营业成本率
    cost_rate = operating_cost / revenue.replace(0, np.nan)
    restructured_data['营业成本率'] = cost_rate
    
    # 毛利
    gross_profit = revenue - operating_cost
    restructured_data['毛利'] = gross_profit
    
    # 毛利率
    gross_profit_rate = gross_profit / revenue.replace(0, np.nan)
    restructured_data['毛利率'] = gross_profit_rate
    
    # ========================================================================
    # 2. 期间费用分析
    # ========================================================================
    logger.info("计算期间费用...")
    
    tax_surcharge = _safe_get_value(df_data, '税金及附加', date_columns)
    selling_expense = _safe_get_value(df_data, '销售费用', date_columns)
    admin_expense = _safe_get_value(df_data, '管理费用', date_columns)
    rd_expense = _safe_get_value(df_data, '研发费用', date_columns)
    # 资产减值损失和信用减值损失在原始数据中是负数(损失),需要取绝对值
    asset_impairment = _safe_get_value(df_data, '资产减值损失', date_columns).abs()
    credit_impairment = _safe_get_value(df_data, '信用减值损失', date_columns).abs()
    
    restructured_data['税金及附加'] = tax_surcharge
    restructured_data['营业税金及附加率'] = tax_surcharge / revenue.replace(0, np.nan)
    restructured_data['销售费用'] = selling_expense
    restructured_data['销售费用率'] = selling_expense / revenue.replace(0, np.nan)
    restructured_data['管理费用'] = admin_expense
    restructured_data['管理费用率'] = admin_expense / revenue.replace(0, np.nan)
    restructured_data['研发费用'] = rd_expense
    restructured_data['研发费用率'] = rd_expense / revenue.replace(0, np.nan)
    restructured_data['资产减值损失'] = asset_impairment
    restructured_data['信用减值损失'] = credit_impairment
    restructured_data['资产减值损失率'] = (asset_impairment + credit_impairment) / revenue.replace(0, np.nan)
    
    # ========================================================================
    # 3. 其他经营收益
    # ========================================================================
    logger.info("计算其他经营收益...")
    
    asset_dispose_income = _safe_get_value(df_data, '资产处置收益', date_columns)
    other_income = _safe_get_value(df_data, '其他收益', date_columns)
    nonoper_income = _safe_get_value(df_data, '营业外收入', date_columns)
    nonoper_expense = _safe_get_value(df_data, '营业外支出', date_columns)
    
    restructured_data['资产处置收益'] = asset_dispose_income
    restructured_data['加：其他收益'] = other_income
    restructured_data['加：营业外收入'] = nonoper_income
    restructured_data['减：营业外支出'] = nonoper_expense
    
    # 营业外收支及其他占营业收入的比例
    other_items = asset_dispose_income + other_income + nonoper_income - nonoper_expense
    restructured_data['营业外收支及其他占营业收入的比例'] = other_items / revenue.replace(0, np.nan)
    
    # ========================================================================
    # 4. 息税前经营利润
    # ========================================================================
    logger.info("计算息税前经营利润...")
    
    ebit_operating = (revenue - operating_cost - tax_surcharge - selling_expense 
                      - admin_expense - rd_expense - asset_impairment - credit_impairment
                      + asset_dispose_income + other_income + nonoper_income - nonoper_expense)
    restructured_data['息税前经营利润'] = ebit_operating
    
    # 息税前经营利润率 = 息税前经营利润 / 营业收入
    ebit_operating_margin = ebit_operating / revenue.replace(0, np.nan)
    restructured_data['息税前经营利润率'] = ebit_operating_margin
    
    # ========================================================================
    # 5. 所得税计算
    # ========================================================================
    logger.info("计算所得税...")
    
    income_tax = _safe_get_value(df_data, '所得税费用', date_columns)
    profit_before_tax_raw = _safe_get_value(df_data, '利润总额', date_columns)
    
    # 长期股权投资收益（通常适用不同税率）
    invest_income = _safe_get_value(df_data, '投资收益', date_columns)
    joint_invest_income = _safe_get_value(df_data, '对联营企业投资收益', date_columns)
    long_term_equity_income = joint_invest_income  # 对联营企业投资收益视为长期股权投资收益
    
    # 计算临时的实际所得税税率（用于金融资产收益和财务费用的税务计算）
    # 注意：这是基于原始利润总额的临时税率，最终会在税前利润重构后重新计算
    taxable_profit_temp = profit_before_tax_raw - long_term_equity_income
    effective_tax_rate_temp = income_tax / taxable_profit_temp.replace(0, np.nan)
    effective_tax_rate_temp = effective_tax_rate_temp.clip(lower=0, upper=1)
    
    # 计算临时的经营利润所得税和息前税后经营利润（用于息前税后利润总额计算）
    # 注意：这些是临时值，最终会在税前利润重构后重新计算
    operating_tax_temp = ebit_operating * effective_tax_rate_temp
    nopat_operating_temp = ebit_operating - operating_tax_temp
    
    # ========================================================================
    # 6. 投资收益分析
    # ========================================================================
    logger.info("计算投资收益...")
    
    restructured_data['投资收益'] = invest_income
    restructured_data['(其中)对联营企业及合营企业的投资收益'] = long_term_equity_income
    
    # 短期投资收益 = 投资收益 - 对联营企业投资收益
    short_term_invest_income = invest_income - long_term_equity_income
    restructured_data['短期投资收益'] = short_term_invest_income
    
    # ========================================================================
    # 7. 金融资产收益
    # ========================================================================
    logger.info("计算金融资产收益...")
    
    # 利息收入：优先从"财务费用:利息收入"获取，因为"利息收入"字段通常为空
    interest_income = _safe_get_value(df_data, '利息收入(财务费用)', date_columns)
    if interest_income.sum() == 0:
        interest_income = _safe_get_value(df_data, '利息收入', date_columns)
    fair_value_change = _safe_get_value(df_data, '公允价值变动收益', date_columns)
    exchange_income = _safe_get_value(df_data, '汇兑收益', date_columns)
    hedging_income = _safe_get_value(df_data, '净敞口套期收益', date_columns)
    other_comprehensive_income = _safe_get_value(df_data, '其他综合收益', date_columns)
    
    restructured_data['(其中)利息收入'] = interest_income
    restructured_data['净敞口套期收益'] = hedging_income
    restructured_data['公允价值变动收益'] = fair_value_change
    restructured_data['汇兑收益'] = exchange_income
    restructured_data['其他综合收益的税后净额'] = other_comprehensive_income
    
    # 息税前金融资产收益（严格按照文档公式）
    # 息税前金融资产收益 = 短期投资收益 + 利息收入 + 净敞口套期收益 + 公允价值变动收益 + 汇兑收益 + 其他综合收益
    financial_income = (short_term_invest_income + interest_income + hedging_income 
                        + fair_value_change + exchange_income + other_comprehensive_income)
    restructured_data['息税前金融资产收益'] = financial_income
    
    # 金融资产收益所得税（使用临时税率）
    financial_tax = financial_income * effective_tax_rate_temp
    restructured_data['金融资产收益所得税'] = financial_tax
    
    # 息前税后金融资产收益
    nopat_financial = financial_income - financial_tax
    restructured_data['息前税后金融资产收益'] = nopat_financial
    
    # ========================================================================
    # 8. 长期股权投资收益（单独列示）
    # ========================================================================
    logger.info("计算长期股权投资收益...")
    
    # 长期股权投资收益 = 对联营企业和合营企业的投资收益
    # 这是税后收益,需要单独列示
    long_term_equity_income_after_tax = long_term_equity_income
    
    # ========================================================================
    # 8. 长期股权投资收益
    # ========================================================================
    logger.info("计算长期股权投资收益...")
    
    # 长期股权投资收益 = 对联营企业和合营企业的投资收益
    restructured_data['长期股权投资收益'] = long_term_equity_income
    
    # ========================================================================
    # 9. 息税前利润总额（按正确公式）
    # ========================================================================
    logger.info("计算息税前利润总额...")
    
    # 正确公式：息税前利润总额 = 息税前经营利润 + 息税前金融资产收益 + 长期股权投资收益
    # 注意：长期股权投资收益是税后收益，其他两项是息税前（未扣税）
    ebit_total = ebit_operating + financial_income + long_term_equity_income
    restructured_data['息税前利润总额'] = ebit_total
    
    # ========================================================================
    # 10. 息前税后利润总额
    # ========================================================================
    logger.info("计算息前税后利润总额...")
    
    # 息前税后利润总额 = 息前税后经营利润 + 息前税后金融资产收益（使用临时值）
    # 注意：这是临时计算，最终会在税前利润重构后重新计算
    nopat_total = nopat_operating_temp + nopat_financial
    restructured_data['息前税后利润总额'] = nopat_total
    
    # ========================================================================
    # 11. 财务费用分析
    # ========================================================================
    logger.info("计算财务费用...")

    financial_expense = _safe_get_value(df_data, '财务费用', date_columns)
    interest_expense = _safe_get_value(df_data, '利息费用', date_columns)
    interest_income_in_finexp = _safe_get_value(df_data, '利息收入(财务费用)', date_columns)

    restructured_data['财务费用'] = financial_expense

    # 真实财务费用 = 财务费用 + 利息收入（加回被扣除的利息收入）
    real_financial_expense = financial_expense + interest_income_in_finexp
    restructured_data['真实财务费用'] = real_financial_expense

    restructured_data['(其中)利息费用'] = interest_expense

    # 财务费用抵税效应 = 真实财务费用 × 实际所得税税率（使用临时税率）
    financial_tax_shield = real_financial_expense * effective_tax_rate_temp
    restructured_data['财务费用抵税效应'] = financial_tax_shield

    # 税后真实财务费用
    aftertax_financial_expense = real_financial_expense - financial_tax_shield
    restructured_data['税后真实财务费用'] = aftertax_financial_expense

    # ========================================================================
    # 12. 税前利润和净利润（按文档公式）
    # ========================================================================
    logger.info("计算净利润...")

    # 按文档公式：税前利润 = 息税前利润总额 - 真实财务费用
    profit_before_tax_calc = ebit_total - real_financial_expense
    restructured_data['税前利润'] = profit_before_tax_calc
    
    restructured_data['减：所得税费用'] = income_tax
    
    # 重新计算实际所得税税率（使用重构后的税前利润）
    # 实际所得税税率 = 所得税费用 / (税前利润 - 长期股权投资收益)
    taxable_profit_recalc = profit_before_tax_calc - long_term_equity_income
    effective_tax_rate_recalc = income_tax / taxable_profit_recalc.replace(0, np.nan)
    effective_tax_rate_recalc = effective_tax_rate_recalc.clip(lower=0, upper=1)  # 保持小数形式，与其他比率一致
    restructured_data['实际所得税税率'] = effective_tax_rate_recalc
    
    # 重新计算经营利润所得税和息前税后经营利润（使用正确的实际所得税税率）
    operating_tax_recalc = ebit_operating * effective_tax_rate_recalc
    restructured_data['经营利润所得税'] = operating_tax_recalc
    
    nopat_operating_recalc = ebit_operating - operating_tax_recalc
    restructured_data['息前税后经营利润'] = nopat_operating_recalc
    
    # 按文档公式：净利润 = 税前利润 - 所得税费用
    net_profit = profit_before_tax_calc - income_tax
    restructured_data['净利润'] = net_profit
    
    # 净利润率
    net_profit_rate = net_profit / revenue.replace(0, np.nan)
    restructured_data['净利润率'] = net_profit_rate
    
    # ========================================================================
    # 13. 股权价值增加值
    # ========================================================================
    logger.info("计算股权价值增加值...")
    
    # 获取所有者权益合计
    total_equity = pd.Series(0.0, index=date_columns)
    if equity_data is not None and '项目' in equity_data.columns:
        equity_row = equity_data[equity_data['项目'] == '所有者权益合计']
        if len(equity_row) > 0:
            for col in date_columns:
                if col in equity_row.columns:
                    val = equity_row[col].values[0]
                    if pd.notna(val):
                        total_equity[col] = val
    
    # 股权资本成本 = 所有者权益合计 × 股权资本成本率
    equity_cost = total_equity * equity_cost_rate
    restructured_data['股权资本成本（默认8%）'] = equity_cost
    
    # 股权价值增加值 = 净利润 - 股权资本成本
    equity_value_added = net_profit - equity_cost
    restructured_data['股权价值增加值'] = equity_value_added
    
    # ========================================================================
    # 创建重构后的DataFrame
    # ========================================================================
    
    # 定义输出顺序
    output_order = [
        '营业收入',
        '营业成本',
        '营业成本率',
        '毛利',
        '毛利率',
        '税金及附加',
        '营业税金及附加率',
        '销售费用',
        '销售费用率',
        '管理费用',
        '管理费用率',
        '研发费用',
        '研发费用率',
        '资产减值损失',
        '信用减值损失',
        '资产减值损失率',
        '资产处置收益',
        '加：其他收益',
        '加：营业外收入',
        '减：营业外支出',
        '营业外收支及其他占营业收入的比例',
        '息税前经营利润',
        '息税前经营利润率',
        '经营利润所得税',
        '息前税后经营利润',
        '投资收益',
        '(其中)对联营企业及合营企业的投资收益',
        '短期投资收益',
        '(其中)利息收入',
        '净敞口套期收益',
        '公允价值变动收益',
        '汇兑收益',
        '其他综合收益的税后净额',
        '息税前金融资产收益',
        '金融资产收益所得税',
        '息前税后金融资产收益',
        '长期股权投资收益',
        '息税前利润总额',
        '息前税后利润总额',
        '财务费用',
        '真实财务费用',
        '(其中)利息费用',
        '财务费用抵税效应',
        '税后真实财务费用',
        '税前利润',
        '减：所得税费用',
        '实际所得税税率',
        '净利润',
        '净利润率',
        '股权资本成本（默认8%）',
        '股权价值增加值',
    ]
    
    # 创建DataFrame
    df_result = pd.DataFrame(restructured_data).T
    
    # 按照预定义顺序排列
    available_items = [item for item in output_order if item in df_result.index]
    df_result = df_result.loc[available_items]
    
    # 重置索引
    df_result = df_result.reset_index()
    df_result = df_result.rename(columns={'index': '项目'})
    
    logger.info(f"利润表重构完成，共 {len(df_result)} 个项目")
    
    return df_result


# ============================================================================
# 辅助函数
# ============================================================================

def _clean_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    清理重复的列名（如 20250930, 20250930.1 等）
    只保留第一个出现的列
    """
    seen = {}
    columns_to_keep = []
    
    for col in df.columns:
        # 去掉 .1, .2 等后缀
        col_str = str(col)
        base_name = col_str.split('.')[0]
        
        if base_name not in seen:
            seen[base_name] = col
            columns_to_keep.append(col)
    
    return df[columns_to_keep].rename(columns={v: k for k, v in seen.items()})


def _standardize_income_field_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化利润表字段名
    """
    new_index = []
    for idx in df.index:
        if idx in INCOME_FIELD_MAPPING:
            new_index.append(INCOME_FIELD_MAPPING[idx])
        else:
            new_index.append(idx)
    
    df.index = new_index
    return df


def _safe_get_value(df: pd.DataFrame, 
                    field_name: str, 
                    date_columns: List[str]) -> pd.Series:
    """
    安全获取字段值
    
    处理重复索引的情况：取第一个非NaN值
    """
    if field_name in df.index:
        val = df.loc[field_name]
        
        # 处理重复索引的情况
        if isinstance(val, pd.DataFrame):
            # 对于每个日期列，取第一个非NaN值
            result = pd.Series(0.0, index=date_columns)
            for col in date_columns:
                col_values = val[col]
                # 找到第一个非NaN值
                non_nan_values = col_values.dropna()
                if len(non_nan_values) > 0:
                    result[col] = non_nan_values.iloc[0]
                else:
                    result[col] = 0
            return result
        elif isinstance(val, pd.Series):
            # 单行情况
            return pd.to_numeric(val, errors='coerce').fillna(0)
        else:
            return pd.Series(0.0, index=date_columns)
    return pd.Series(0.0, index=date_columns)


# ============================================================================
# 主函数测试
# ============================================================================

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 读取测试数据
    test_file = 'data/601898.SH_income.csv'
    df = pd.read_csv(test_file, encoding='utf-8-sig')
    
    print("原始数据形状:", df.shape)
    print("\n原始数据前10行:")
    print(df.head(10))
    
    # 重构利润表
    df_restructured = restructure_income_statement(df)
    
    print("\n重构后数据形状:", df_restructured.shape)
    print("\n重构后数据:")
    print(df_restructured.to_string())
    
    # 保存结果
    output_file = 'data/601898.SH_income_restructured.csv'
    df_restructured.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n重构后的利润表已保存到: {output_file}")
