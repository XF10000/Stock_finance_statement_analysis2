"""
资产负债表重构模块
将传统资产负债表重构为"资产-资本"结构
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging


# ============================================================================
# 统一字段名映射（支持英文和中文字段名）
# ============================================================================

# 创建一个统一的字段名映射字典，将所有可能的字段名映射到标准名称
UNIFIED_FIELD_MAPPING = {
    # 流动金融资产
    'money_cap': '货币资金',
    '货币资金': '货币资金',
    'loanto_oth_bank_fi': '拆出资金',
    '拆出资金': '拆出资金',
    'trad_asset': '交易性金融资产',
    '交易性金融资产': '交易性金融资产',
    'deriv_assets': '衍生金融资产',
    '衍生金融资产': '衍生金融资产',
    'int_receiv': '应收利息',
    '应收利息': '应收利息',
    'div_receiv': '应收股利',
    '应收股利': '应收股利',
    'pur_resale_fa': '买入返售金融资产',
    '买入返售金融资产': '买入返售金融资产',
    'hfs_assets': '持有待售资产',
    '持有待售资产': '持有待售资产',
    'nca_within_1y': '一年内到期的非流动资产',
    '一年内到期的非流动资产': '一年内到期的非流动资产',
    
    # 非流动金融资产
    'loans_oth_bank': '发放贷款及垫款',
    '发放贷款及垫款': '发放贷款及垫款',
    '发放贷款及垫款(流动)': '发放贷款及垫款(流动)',
    '发放贷款及垫款(非流动)': '发放贷款及垫款(非流动)',
    'debt_invest': '债权投资',
    '债权投资': '债权投资',
    'oth_debt_invest': '其他债权投资',
    '其他债权投资': '其他债权投资',
    'oth_eqt_tools': '其他权益工具投资',
    '其他权益工具投资': '其他权益工具投资',
    'oth_illiq_fin_assets': '其他非流动金融资产',
    '其他非流动金融资产': '其他非流动金融资产',
    'invest_real_estate': '投资性房地产',
    '投资性房地产': '投资性房地产',
    
    # 长期股权投资
    'lt_eqt_invest': '长期股权投资',
    '长期股权投资': '长期股权投资',
    'oth_eq_invest': '其他权益工具投资',
    
    # 营运资产
    'notes_receiv': '应收票据',
    '应收票据': '应收票据',
    'accounts_receiv': '应收账款',
    '应收账款': '应收账款',
    'receiv_financing': '应收款项融资',
    '应收款项融资': '应收款项融资',
    'prepayment': '预付款项',
    '预付款项': '预付款项',
    'oth_receiv': '其他应收款',
    '其他应收款': '其他应收款',
    '其他应收款合计': '其他应收款合计',
    'inventories': '存货',
    '存货': '存货',
    'contract_assets': '合同资产',
    '合同资产': '合同资产',
    'lt_rec': '长期应收款',
    '长期应收款': '长期应收款',
    'oth_cur_assets': '其他流动资产',
    '其他流动资产': '其他流动资产',
    'settlement_provisions': '结算备付金',
    '结算备付金': '结算备付金',
    'premium_receiv': '应收保费',
    '应收保费': '应收保费',
    'reinsur_receiv': '应收分保账款',
    '应收分保账款': '应收分保账款',
    'reinsur_reser_receiv': '应收分保合同准备金',
    '应收分保合同准备金': '应收分保合同准备金',
    'insur_contract_reser': '保险合同准备金',
    '保险合同准备金': '保险合同准备金',
    
    # 营运负债
    'notes_payable': '应付票据',
    '应付票据': '应付票据',
    'acct_payable': '应付账款',
    '应付账款': '应付账款',
    'adv_receipts': '预收款项',
    '预收款项': '预收款项',
    'contract_liab': '合同负债',
    '合同负债': '合同负债',
    'payroll_payable': '应付职工薪酬',
    '应付职工薪酬': '应付职工薪酬',
    'lt_payroll_payable': '长期应付职工薪酬',
    '长期应付职工薪酬': '长期应付职工薪酬',
    'taxes_payable': '应交税费',
    '应交税费': '应交税费',
    'oth_payable': '其他应付款',
    '其他应付款': '其他应付款',
    '其他应付款合计': '其他应付款合计',
    'oth_cur_liab': '其他流动负债',
    '其他流动负债': '其他流动负债',
    'agency_bus_liab': '应付手续费及佣金',
    '应付手续费及佣金': '应付手续费及佣金',
    'reinsur_payable': '应付分保账款',
    '应付分保账款': '应付分保账款',
    'provisions': '预计负债',
    '预计负债': '预计负债',
    '预计负债(流动)': '预计负债(流动)',
    '预计负债(非流动)': '预计负债(非流动)',
    'defer_reve_within_1y': '一年内到期的递延收益',
    '一年内到期的递延收益': '一年内到期的递延收益',
    'defer_reve': '递延收益-非流动负债',
    '递延收益-非流动负债': '递延收益-非流动负债',
    '长期递延收益': '递延收益-非流动负债',
    'oth_ncl': '其他非流动负债',
    '其他非流动负债': '其他非流动负债',
    'div_payable': '应付股利',
    '应付股利': '应付股利',
    
    # 长期经营资产
    'fix_assets': '固定资产',
    '固定资产': '固定资产',
    'fix_assets_total': '固定资产合计',
    '固定资产合计': '固定资产合计',
    'cip': '在建工程',
    '在建工程': '在建工程',
    'constr_in_process': '在建工程合计',
    '在建工程合计': '在建工程合计',
    '工程物资': '工程物资',
    'const_materials': '工程物资',
    'produc_bio_assets': '生产性生物资产',
    '生产性生物资产': '生产性生物资产',
    'public_welfare_bio_assets': '公益性生物资产',
    '公益性生物资产': '公益性生物资产',
    'oil_and_gas_assets': '油气资产',
    '油气资产': '油气资产',
    'use_right_assets': '使用权资产',
    '使用权资产': '使用权资产',
    'intan_assets': '无形资产',
    '无形资产': '无形资产',
    'r_and_d': '开发支出',
    '开发支出': '开发支出',
    '研发支出': '开发支出',  # 原始数据中的字段名
    'goodwill': '商誉',
    '商誉': '商誉',
    'lt_amor_exp': '长期待摊费用',
    '长期待摊费用': '长期待摊费用',
    'oth_assets': '其他非流动资产',
    '其他非流动资产': '其他非流动资产',
    'defer_tax_assets': '递延所得税资产',
    '递延所得税资产': '递延所得税资产',
    'defer_tax_liab': '递延所得税负债',
    '递延所得税负债': '递延所得税负债',
    
    # 短期债务
    'st_borr': '短期借款',
    '短期借款': '短期借款',
    'cb_borr': '向中央银行借款',
    '向中央银行借款': '向中央银行借款',
    'loan_oth_bank': '拆入资金',
    '拆入资金': '拆入资金',
    'trading_fl': '交易性金融负债',
    '交易性金融负债': '交易性金融负债',
    'deriv_liab': '衍生金融负债',
    '衍生金融负债': '衍生金融负债',
    'sold_for_repur_fa': '卖出回购金融资产',
    '卖出回购金融资产款': '卖出回购金融资产',
    'accept_money_dep': '吸收存款及同业存放',
    '吸收存款及同业存放': '吸收存款及同业存放',
    'agency_bus_sec_pro': '代理买卖证券款',
    '代理买卖证券款': '代理买卖证券款',
    'agency_undr_sec_pro': '代理承销证券款',
    '代理承销证券款': '代理承销证券款',
    'int_payable': '应付利息',
    '应付利息': '应付利息',
    'hfs_sales': '持有待售负债',
    '持有待售负债': '持有待售负债',
    'non_cur_liab_due_1y': '一年内到期的非流动负债',
    '一年内到期的非流动负债': '一年内到期的非流动负债',
    
    # 长期债务
    'lt_borr': '长期借款',
    '长期借款': '长期借款',
    'bond_payable': '应付债券',
    '应付债券': '应付债券',
    'lease_liab': '租赁负债',
    '租赁负债': '租赁负债',
    'lt_payable': '长期应付款',
    '长期应付款': '长期应付款',
    '长期应付款合计': '长期应付款合计',
    
    # 所有者权益
    'total_share': '期末总股本',
    '期末总股本': '期末总股本',
    'oth_eqt_tools': '其他权益工具',
    '其他权益工具': '其他权益工具',
    '优先股': '优先股',
    '永续债': '永续债',
    '外币报表折算差额': '外币报表折算差额',
    'cap_rese': '资本公积金',
    '资本公积金': '资本公积金',
    'treasury_share': '库存股',
    '库存股': '库存股',
    'oth_comp_income': '其他综合收益',
    '其他综合收益': '其他综合收益',
    'special_rese': '专项储备',
    '专项储备': '专项储备',
    'surplus_rese': '盈余公积金',
    '盈余公积金': '盈余公积金',
    'ordin_risk_reser': '一般风险准备',
    '一般风险准备': '一般风险准备',
    'undistr_porfit': '未分配利润',
    '未分配利润': '未分配利润',
    'minority_int': '少数股东权益',
    '少数股东权益': '少数股东权益',
    
    # 其他
    'total_assets': '资产总计',
    '资产总计': '资产总计',
    'total_liab': '负债合计',
    '负债合计': '负债合计',
    'total_eqt': '所有者权益合计',
    '所有者权益合计': '所有者权益合计',
    'div_payable': '应付股利',
    '应付股利': '应付股利',
}


# ============================================================================
# 字段分组配置（用于计算各个合计项）
# ============================================================================

# 金融资产字段列表
# 文档公式: 货币资金 + 拆出资金 + 交易性金融资产 + 衍生金融资产(流动) + 应收利息 + 应收股利 
#          + 买入返售金融资产 + 持有待售资产 + 一年内到期的非流动资产 + 发放贷款及垫款(流动) 
#          + 发放贷款及垫款(非流动) + 债权投资 + 其他债权投资 + 其他权益工具投资 
#          + 其他非流动金融资产 + 投资性房地产
# 历史会计准则字段(2019年前): 可供出售金融资产、持有至到期投资、应收款项类投资
# 注意: 这些字段在2019年新金融工具准则实施后不再使用，但历史数据需要计入金融资产
FINANCIAL_ASSETS_FIELDS = [
    '货币资金', '拆出资金', '交易性金融资产', '衍生金融资产', 
    '应收利息', '应收股利', '买入返售金融资产', '持有待售资产',
    '一年内到期的非流动资产', '发放贷款及垫款', '债权投资', '其他债权投资', 
    '其他权益工具投资', '其他非流动金融资产', '投资性房地产',
    # 历史会计准则字段（2019年前）
    '可供出售金融资产', '持有至到期投资', '应收款项类投资'
]

# 长期股权投资字段列表
LONG_TERM_EQUITY_FIELDS = [
    '长期股权投资',
]

# 营运资产字段列表
OPERATING_ASSETS_FIELDS = [
    '应收票据', '应收账款', '应收款项融资', '预付款项',
    '其他应收款', '其他应收款合计', '存货', '合同资产', '长期应收款', '其他流动资产',
    '结算备付金', '应收保费', '应收分保账款', '应收分保合同准备金', '保险合同准备金',
]

# 营运负债字段列表（严格按照文档）
# 营运负债小计 = 应付票据 + 应付账款 + 预收账款 + 合同负债 + 应付职工薪酬 + 长期应付职工薪酬 
#              + 应交税费 + 其他应付款 + 应付手续费及佣金 + 应付分保账款 + 其他流动负债 
#              + 预计负债(流动) + 预计负债(非流动) + 一年内到期的递延收益 + 长期递延收益 + 其他非流动负债
OPERATING_LIABILITIES_FIELDS = [
    '应付票据', '应付账款', '预收款项', '合同负债',
    '应付职工薪酬', '长期应付职工薪酬', '应交税费',
    '其他应付款', '其他应付款合计', '其他流动负债', 
    '应付手续费及佣金', '应付分保账款', 
    '预计负债', '预计负债(流动)', '预计负债(非流动)',
    '一年内到期的递延收益', '递延收益-非流动负债', '长期递延收益', '其他非流动负债',
]

# 长期经营资产字段列表
LONG_TERM_OPERATING_ASSETS_FIELDS = [
    '固定资产', '固定资产合计', '在建工程合计', '生产性生物资产', '公益性生物资产', '油气资产',
    '使用权资产', '无形资产', '开发支出', '商誉', '长期待摊费用',
    '其他非流动资产', '递延所得税资产'
]

# 短期债务字段列表
SHORT_TERM_DEBT_FIELDS = [
    '短期借款', '向中央银行借款', '拆入资金', '交易性金融负债',
    '衍生金融负债', '卖出回购金融资产', '吸收存款及同业存放', 
    '代理买卖证券款', '代理承销证券款', '应付利息',
    '持有待售负债', '一年内到期的非流动负债',
]

# 长期债务字段列表
LONG_TERM_DEBT_FIELDS = [
    '长期借款', '应付债券', '租赁负债', '长期应付款', '长期应付款合计',
]

# 所有者权益字段列表（加项）
EQUITY_POSITIVE_FIELDS = [
    '期末总股本', '其他权益工具', '资本公积金', '其他综合收益',
    '专项储备', '盈余公积金', '一般风险准备', '未分配利润',
]

# 所有者权益字段列表（减项）
EQUITY_NEGATIVE_FIELDS = [
    '库存股',
]


# ============================================================================
# 资产负债表重构函数
# ============================================================================

def restructure_balance_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """
    重构资产负债表：将传统结构转换为资产-资本结构
    
    Args:
        df: 原始资产负债表数据
            - 原始格式：每一行是一个报告期，字段名为列（如tushare返回的格式）
            - 转置格式：字段名为行，日期为列（可选）
        
    Returns:
        重构后的资产负债表 DataFrame
    """
    logger = logging.getLogger(__name__)
    
    # 确保数据格式正确
    if '字段名' in df.columns:
        # 已经是转置格式：字段名为第一列
        df_data = df.set_index('字段名')
        logger.info("输入数据为转置格式")
    elif '报告期' in df.columns or 'end_date' in df.columns:
        # 原始格式：需要转置
        logger.info("输入数据为原始格式，进行转置...")
        
        # 确定报告期列名
        date_col = '报告期' if '报告期' in df.columns else 'end_date'
        
        # 获取数值列（排除非数值列）
        non_numeric_cols = ['TS股票代码', 'ts_code', '公告日期', 'ann_date', '实际公告日期', 'f_ann_date',
                           '报告期', 'end_date', '报表类型', 'report_type', '公司类型', 'comp_type',
                           '报告期类型', 'end_type', '更新标识', 'update_flag']
        numeric_cols = [col for col in df.columns if col not in non_numeric_cols]
        
        # 提取数值部分和报告期
        df_work = df[[date_col] + numeric_cols].copy()
        
        # 设置报告期为索引，然后转置
        df_work = df_work.set_index(date_col)
        df_data = df_work.T
        
        # 现在索引是字段名，列是日期
        # 重置索引，让字段名成为一列
        df_data = df_data.reset_index()
        df_data = df_data.rename(columns={'index': '字段名'})
        df_data = df_data.set_index('字段名')
        
        logger.info(f"转置完成，数据形状: {df_data.shape}")
    else:
        # 未知格式
        logger.warning("无法识别数据格式，假设已经是正确格式")
        df_data = df.copy()
    
    # 标准化字段名（将所有字段名映射到标准名称）
    df_data = _standardize_field_names(df_data)
    
    # 获取所有日期列
    date_columns = df_data.columns.tolist()
    
    # 创建重构后的数据结构
    restructured_data = {}
    
    # ========================================================================
    # 资产结构
    # ========================================================================
    
    # 1. 金融资产合计
    logger.info("计算金融资产...")
    financial_assets = _calculate_sum(df_data, FINANCIAL_ASSETS_FIELDS, date_columns)
    restructured_data['金融资产合计'] = financial_assets
    
    # 添加金融资产明细
    for field in FINANCIAL_ASSETS_FIELDS:
        if field in df_data.index:
            try:
                val = df_data.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                restructured_data[field] = val
            except:
                pass
    
    # 2. 长期股权投资
    logger.info("计算长期股权投资...")
    long_term_equity = _calculate_sum(df_data, LONG_TERM_EQUITY_FIELDS, date_columns)
    restructured_data['长期股权投资'] = long_term_equity
    
    # 3. 经营资产合计
    logger.info("计算经营资产...")
    
    # 3.1 营运资产小计
    operating_assets = _calculate_operating_assets(df_data, date_columns)
    restructured_data['营运资产小计'] = operating_assets
    
    # 添加营运资产明细（包含调整后的其他应收款）
    for field in OPERATING_ASSETS_FIELDS:
        if field in df_data.index:
            try:
                val = df_data.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                    
                if field == '其他应收款':
                    # 添加原始值和调整后值
                    restructured_data['其他应收款(原值)'] = val
                    adjusted = _adjust_other_receivables(df_data, date_columns)
                    restructured_data['其他应收款(调整后)'] = adjusted
                else:
                    restructured_data[field] = val
            except:
                pass
    
    # 3.2 营运负债小计
    operating_liabilities = _calculate_operating_liabilities(df_data, date_columns)
    restructured_data['营运负债小计'] = operating_liabilities
    
    # 添加营运负债明细
    for field in OPERATING_LIABILITIES_FIELDS:
        if field in df_data.index:
            try:
                val = df_data.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                restructured_data[field] = val
            except:
                pass
    
    # 添加应付股利（单独列示）
    if '应付股利' in df_data.index:
        try:
            val = df_data.loc['应付股利']
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            restructured_data['应付股利'] = val
        except:
            pass
    
    # 3.3 周转性经营投入合计
    working_capital = operating_assets - operating_liabilities
    restructured_data['周转性经营投入合计'] = working_capital
    
    # 3.4 长期经营资产合计
    long_term_operating_assets = _calculate_long_term_operating_assets(df_data, date_columns)
    restructured_data['长期经营资产合计'] = long_term_operating_assets
    
    # 添加长期经营资产明细
    for field in LONG_TERM_OPERATING_ASSETS_FIELDS:
        if field in df_data.index:
            try:
                val = df_data.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                
                # 特殊处理固定资产：如果为空，使用固定资产合计的值
                if field == '固定资产':
                    # 获取固定资产合计的值
                    fix_assets_total_val = None
                    if '固定资产合计' in df_data.index:
                        try:
                            fix_assets_total_val = df_data.loc['固定资产合计']
                            if isinstance(fix_assets_total_val, pd.DataFrame):
                                fix_assets_total_val = fix_assets_total_val.iloc[0]
                        except:
                            pass
                    
                    # 逐期填充：如果固定资产为空，使用固定资产合计
                    if fix_assets_total_val is not None:
                        merged_val = val.copy()
                        for date_col in date_columns:
                            if pd.isna(merged_val.get(date_col)) and pd.notna(fix_assets_total_val.get(date_col)):
                                merged_val[date_col] = fix_assets_total_val.get(date_col)
                        restructured_data[field] = merged_val
                    else:
                        restructured_data[field] = val
                else:
                    restructured_data[field] = val
            except:
                pass
    
    # 添加递延所得税负债（作为减项）
    if '递延所得税负债' in df_data.index:
        try:
            val = df_data.loc['递延所得税负债']
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            restructured_data['递延所得税负债(减项)'] = val
        except:
            pass
    
    # 3.5 经营资产合计
    total_operating_assets = working_capital + long_term_operating_assets
    restructured_data['经营资产合计'] = total_operating_assets
    
    # 资产总额
    total_assets = financial_assets + long_term_equity + total_operating_assets
    restructured_data['资产总额'] = total_assets
    
    # ========================================================================
    # 资本结构
    # ========================================================================
    
    # 4. 有息债务合计
    logger.info("计算有息债务...")
    
    # 4.1 短期债务
    short_term_debt = _calculate_sum(df_data, SHORT_TERM_DEBT_FIELDS, date_columns)
    restructured_data['短期债务'] = short_term_debt
    
    # 添加短期债务明细
    for field in SHORT_TERM_DEBT_FIELDS:
        if field in df_data.index:
            try:
                val = df_data.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                restructured_data[field] = val
            except:
                pass
    
    # 4.2 长期债务（优先使用合计字段）
    long_term_debt = _calculate_long_term_debt(df_data, date_columns)
    restructured_data['长期债务'] = long_term_debt
    
    # 添加长期债务明细
    for field in LONG_TERM_DEBT_FIELDS:
        if field in df_data.index:
            try:
                val = df_data.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                restructured_data[field] = val
            except:
                pass
    
    # 4.3 有息债务合计
    total_debt = short_term_debt + long_term_debt
    restructured_data['有息债务合计'] = total_debt
    
    # 5. 所有者权益合计
    logger.info("计算所有者权益...")
    
    # 5.1 归属于母公司股东权益合计
    parent_equity = _calculate_parent_equity(df_data, date_columns)
    restructured_data['归属于母公司股东权益合计'] = parent_equity
    
    # 添加股东权益明细
    for field in EQUITY_POSITIVE_FIELDS + EQUITY_NEGATIVE_FIELDS:
        if field in df_data.index:
            try:
                val = df_data.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                restructured_data[field] = val
            except:
                pass
    
    # 5.2 少数股东权益
    if '少数股东权益' in df_data.index:
        try:
            val = df_data.loc['少数股东权益']
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            # 将NaN填充为0，避免影响所有者权益合计的计算
            minority_interest = pd.to_numeric(val, errors='coerce').fillna(0)
        except:
            minority_interest = pd.Series(0, index=date_columns)
    else:
        minority_interest = pd.Series(0, index=date_columns)
    restructured_data['少数股东权益'] = minority_interest
    
    # 5.3 所有者权益合计
    total_equity = parent_equity + minority_interest
    restructured_data['所有者权益合计'] = total_equity
    
    # 资本总额
    total_capital = total_equity + total_debt
    restructured_data['资本总额'] = total_capital
    
    # ========================================================================
    # 创建重构后的DataFrame
    # ========================================================================
    
    # 定义输出顺序
    output_order = [
        # 资产结构
        '金融资产合计',
        '货币资金', '交易性金融资产', '应收利息', '应收股利', 
        '买入返售金融资产', '持有待售资产', '一年内到期的非流动资产',
        '债权投资', '其他债权投资', '其他权益工具投资', 
        '其他非流动金融资产', '投资性房地产',
        '长期股权投资',
        '经营资产合计',
        '周转性经营投入合计',
        '营运资产小计',
        '应收票据', '应收账款', '应收款项融资', '预付款项',
        '其他应收款(原值)', '其他应收款(调整后)', '存货', '合同资产', 
        '长期应收款', '其他流动资产',
        '营运负债小计',
        '应付票据', '应付账款', '预收款项', '合同负债',
        '应付职工薪酬', '长期应付职工薪酬', '应交税费',
        '其他应付款', '应付股利', '其他流动负债', '递延收益-非流动负债',
        '长期经营资产合计',
        '固定资产', '固定资产合计', '在建工程合计', '生产性生物资产', '油气资产',
        '使用权资产', '无形资产', '开发支出', '商誉', '长期待摊费用',
        '其他非流动资产', '递延所得税资产', '递延所得税负债(减项)',
        '资产总额',
        
        # 资本结构
        '有息债务合计',
        '短期债务',
        '短期借款', '拆入资金', '交易性金融负债',
        '应付利息', '持有待售负债', '一年内到期的非流动负债',
        '长期债务',
        '长期借款', '应付债券', '租赁负债', '长期应付款',
        '所有者权益合计',
        '归属于母公司股东权益合计',
        '期末总股本', '资本公积金', '库存股',
        '其他综合收益', '专项储备', '盈余公积金', '一般风险准备', '未分配利润',
        '少数股东权益',
        '资本总额',
    ]
    
    # 创建DataFrame
    df_result = pd.DataFrame(restructured_data).T
    
    # 按照预定义顺序排列
    available_items = [item for item in output_order if item in df_result.index]
    df_result = df_result.loc[available_items]
    
    # 重置索引
    df_result = df_result.reset_index()
    df_result = df_result.rename(columns={'index': '项目'})
    
    logger.info(f"资产负债表重构完成，共 {len(df_result)} 个项目")
    
    return df_result


# ============================================================================
# 辅助函数
# ============================================================================

def _standardize_field_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化字段名：将所有字段名映射到标准名称
    
    Args:
        df: 原始DataFrame
        
    Returns:
        字段名标准化后的DataFrame
    """
    # 创建新的索引
    new_index = []
    for idx in df.index:
        # 如果字段名在映射字典中，使用标准名称
        if idx in UNIFIED_FIELD_MAPPING:
            new_index.append(UNIFIED_FIELD_MAPPING[idx])
        else:
            new_index.append(idx)
    
    df.index = new_index
    return df


def _calculate_sum(df: pd.DataFrame, 
                   field_list: List[str],
                   date_columns: List[str]) -> pd.Series:
    """
    计算字段列表的合计值
    
    Args:
        df: 数据DataFrame
        field_list: 字段列表
        date_columns: 日期列列表
        
    Returns:
        合计Series
    """
    total = pd.Series(0.0, index=date_columns)
    
    for field in field_list:
        if field in df.index:
            # 处理可能的重复索引，取第一个
            try:
                values = df.loc[field]
                if isinstance(values, pd.DataFrame):
                    # 如果有重复，取第一个
                    values = values.iloc[0]
                values = pd.to_numeric(values, errors='coerce').fillna(0)
                total = total + values
            except Exception as e:
                logging.warning(f"计算字段 {field} 时出错: {e}")
                continue
    
    return total


def _adjust_other_receivables(df: pd.DataFrame, 
                              date_columns: List[str]) -> pd.Series:
    """
    调整其他应收款：扣除应收利息和应收股利
    
    其他应收款(调整后) = 其他应收款(或其他应收款合计) - 应收利息 - 应收股利
    
    注意：优先使用"其他应收款合计"，因为原始数据中"其他应收款"可能为空
    """
    def safe_get_value(field_name):
        if field_name in df.index:
            val = df.loc[field_name]
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            return pd.to_numeric(val, errors='coerce').fillna(0)
        return pd.Series(0.0, index=date_columns)
    
    # 优先使用其他应收款合计
    other_receiv_total = safe_get_value('其他应收款合计')
    if other_receiv_total.sum() == 0:
        other_receiv_total = safe_get_value('其他应收款')
    
    int_receiv = safe_get_value('应收利息')
    div_receiv = safe_get_value('应收股利')
    
    adjusted = other_receiv_total - int_receiv - div_receiv
    return adjusted


def _adjust_other_payables(df: pd.DataFrame,
                          date_columns: List[str]) -> pd.Series:
    """
    调整其他应付款：扣除应付利息和应付股利
    
    其他应付款(调整后) = 其他应付款(或其他应付款合计) - 应付利息 - 应付股利
    
    注意：优先使用"其他应付款合计"，因为原始数据中"其他应付款"可能为空
    """
    def safe_get_value(field_name):
        if field_name in df.index:
            val = df.loc[field_name]
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            return pd.to_numeric(val, errors='coerce').fillna(0)
        return pd.Series(0.0, index=date_columns)
    
    # 优先使用其他应付款合计
    other_pay_total = safe_get_value('其他应付款合计')
    if other_pay_total.sum() == 0:
        other_pay_total = safe_get_value('其他应付款')
    
    int_payable = safe_get_value('应付利息')
    div_payable = safe_get_value('应付股利')
    
    adjusted = other_pay_total - int_payable - div_payable
    return adjusted


def _calculate_operating_assets(df: pd.DataFrame,
                                date_columns: List[str]) -> pd.Series:
    """
    计算营运资产小计
    
    营运资产小计 = 应收票据 + 应收账款 + 应收款项融资 + 预付款项 + 其他应收款(调整后) 
                 + 存货 + 合同资产 + 长期应收款 + 其他流动资产
    
    注意：其他应收款使用调整后的值，优先使用"其他应收款合计"
    """
    total = pd.Series(0.0, index=date_columns)
    
    # 使用调整后的其他应收款
    other_receiv_adjusted = _adjust_other_receivables(df, date_columns)
    other_receiv_used = False
    
    for field in OPERATING_ASSETS_FIELDS:
        if field in ['其他应收款', '其他应收款合计']:
            continue  # 单独处理
        
        if field in df.index:
            try:
                val = df.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                values = pd.to_numeric(val, errors='coerce').fillna(0)
                total = total + values
            except Exception as e:
                logging.warning(f"计算字段 {field} 时出错: {e}")
                continue
    
    # 添加调整后的其他应收款
    total = total + other_receiv_adjusted
    
    return total


def _calculate_operating_liabilities(df: pd.DataFrame,
                                     date_columns: List[str]) -> pd.Series:
    """
    计算营运负债小计
    
    营运负债小计 = 应付票据 + 应付账款 + 预收账款 + 合同负债 + 应付职工薪酬 + 长期应付职工薪酬
                 + 应交税费 + 其他应付款(调整后) + 其他流动负债 + 长期递延收益
    
    注意：其他应付款使用调整后的值（扣除应付股利），优先使用"其他应付款合计"
    """
    total = pd.Series(0.0, index=date_columns)
    
    # 使用调整后的其他应付款
    other_pay_adjusted = _adjust_other_payables(df, date_columns)
    
    for field in OPERATING_LIABILITIES_FIELDS:
        if field in ['其他应付款', '其他应付款合计']:
            continue  # 单独处理
        
        if field in df.index:
            try:
                val = df.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                values = pd.to_numeric(val, errors='coerce').fillna(0)
                total = total + values
            except Exception as e:
                logging.warning(f"计算字段 {field} 时出错: {e}")
                continue
    
    # 添加调整后的其他应付款
    total = total + other_pay_adjusted
    
    return total


def _calculate_long_term_operating_assets(df: pd.DataFrame,
                                          date_columns: List[str]) -> pd.Series:
    """
    计算长期经营资产合计
    
    长期经营资产合计 = 固定资产(或固定资产合计) + 在建工程 + 生产性生物资产 + 油气资产 + 使用权资产
                      + 无形资产 + 开发支出 + 商誉 + 长期待摊费用 + 其他非流动资产
                      + 递延所得税资产 - 递延所得税负债
    
    注意：固定资产和固定资产合计只会使用其中一个，优先使用固定资产合计（非空值）
    """
    total = pd.Series(0.0, index=date_columns)
    
    # 处理固定资产字段：逐期判断，优先使用固定资产合计的非空值
    fixed_assets_values = pd.Series(0.0, index=date_columns)
    
    # 获取两个字段的数据
    fix_assets_total = None
    fix_assets = None
    
    if '固定资产合计' in df.index:
        try:
            val = df.loc['固定资产合计']
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            fix_assets_total = pd.to_numeric(val, errors='coerce')
        except Exception as e:
            logging.warning(f"读取固定资产合计时出错: {e}")
    
    if '固定资产' in df.index:
        try:
            val = df.loc['固定资产']
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            fix_assets = pd.to_numeric(val, errors='coerce')
        except Exception as e:
            logging.warning(f"读取固定资产时出错: {e}")
    
    # 逐期判断：优先使用固定资产合计的非空值
    for date in date_columns:
        value = 0.0
        # 优先使用固定资产合计
        if fix_assets_total is not None and pd.notna(fix_assets_total.get(date)):
            value = fix_assets_total.get(date, 0.0)
        # 如果固定资产合计为空，使用固定资产
        elif fix_assets is not None and pd.notna(fix_assets.get(date)):
            value = fix_assets.get(date, 0.0)
        
        fixed_assets_values[date] = value if pd.notna(value) else 0.0
    
    total = total + fixed_assets_values
    
    # 处理其他字段（排除固定资产和固定资产合计）
    for field in LONG_TERM_OPERATING_ASSETS_FIELDS:
        if field in ['固定资产', '固定资产合计']:
            continue  # 已经单独处理过了
        if field in df.index:
            try:
                val = df.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                values = pd.to_numeric(val, errors='coerce').fillna(0)
                total = total + values
            except Exception as e:
                logging.warning(f"计算字段 {field} 时出错: {e}")
                continue
    
    # 减项：递延所得税负债
    if '递延所得税负债' in df.index:
        try:
            val = df.loc['递延所得税负债']
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            deferred_tax_liab = pd.to_numeric(val, errors='coerce').fillna(0)
            total = total - deferred_tax_liab
        except Exception as e:
            logging.warning(f"计算递延所得税负债时出错: {e}")
    
    return total


def _calculate_long_term_debt(df: pd.DataFrame,
                               date_columns: List[str]) -> pd.Series:
    """
    计算长期债务
    
    长期债务 = 长期借款 + 应付债券 + 租赁负债 + 长期应付款
    
    注意：优先使用"长期应付款合计"，因为原始数据中"长期应付款"可能为空
    """
    total = pd.Series(0.0, index=date_columns)
    
    def safe_get_value(field_name):
        if field_name in df.index:
            val = df.loc[field_name]
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            return pd.to_numeric(val, errors='coerce').fillna(0)
        return pd.Series(0.0, index=date_columns)
    
    # 处理长期应付款：优先使用合计
    lt_payable_total = safe_get_value('长期应付款合计')
    if lt_payable_total.sum() == 0:
        lt_payable_total = safe_get_value('长期应付款')
    total = total + lt_payable_total
    
    # 其他字段
    for field in ['长期借款', '应付债券', '租赁负债']:
        if field in df.index:
            try:
                val = df.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                values = pd.to_numeric(val, errors='coerce').fillna(0)
                total = total + values
            except Exception as e:
                logging.warning(f"计算字段 {field} 时出错: {e}")
                continue
    
    return total


def _calculate_parent_equity(df: pd.DataFrame,
                            date_columns: List[str]) -> pd.Series:
    """
    计算归属于母公司股东权益合计
    
    归属于母公司股东权益 = 股本 + 其他权益工具 + 资本公积 - 库存股 + 其他综合收益
                          + 专项储备 + 盈余公积 + 一般风险准备 + 未分配利润 + 应付股利
    
    注意：根据参考文件的处理方式，应付股利被计入所有者权益（虽然会计准则上它是负债）
    """
    total = pd.Series(0.0, index=date_columns)
    
    # 加项
    for field in EQUITY_POSITIVE_FIELDS:
        if field in df.index:
            try:
                val = df.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                values = pd.to_numeric(val, errors='coerce').fillna(0)
                total = total + values
            except Exception as e:
                logging.warning(f"计算字段 {field} 时出错: {e}")
                continue
    
    # 减项
    for field in EQUITY_NEGATIVE_FIELDS:
        if field in df.index:
            try:
                val = df.loc[field]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                values = pd.to_numeric(val, errors='coerce').fillna(0)
                total = total - values
            except Exception as e:
                logging.warning(f"计算字段 {field} 时出错: {e}")
                continue
    
    # 加上应付股利（按照参考文件的处理方式）
    if '应付股利' in df.index:
        try:
            val = df.loc['应付股利']
            if isinstance(val, pd.DataFrame):
                val = val.iloc[0]
            values = pd.to_numeric(val, errors='coerce').fillna(0)
            total = total + values
        except Exception as e:
            logging.warning(f"计算字段 应付股利 时出错: {e}")
    
    return total


# ============================================================================
# 主函数测试
# ============================================================================

if __name__ == '__main__':
    # 测试代码
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 读取测试数据
    test_file = 'data/603345.SH_balancesheet.csv'
    df = pd.read_csv(test_file, encoding='utf-8-sig')
    
    print("原始数据形状:", df.shape)
    print("\n原始数据前10行:")
    print(df.head(10))
    
    # 重构资产负债表
    df_restructured = restructure_balance_sheet(df)
    
    print("\n重构后数据形状:", df_restructured.shape)
    print("\n重构后数据前30行:")
    print(df_restructured.head(30))
    
    # 保存结果
    output_file = 'data/603345.SH_balancesheet_restructured.csv'
    df_restructured.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n重构后的资产负债表已保存到: {output_file}")
    
    # 验证数据正确性
    print("\n" + "="*60)
    print("数据验证:")
    print("="*60)
    
    # 检查某一期的数据
    test_date = '20250930'
    print(f"\n检查 {test_date} 期数据:")
    
    # 金融资产合计
    print(f"金融资产合计: {df_restructured[df_restructured['项目']=='金融资产合计'][test_date].values[0]:,.2f}")
    print(f"  货币资金: {df_restructured[df_restructured['项目']=='货币资金'][test_date].values[0]:,.2f}")
    print(f"  交易性金融资产: {df_restructured[df_restructured['项目']=='交易性金融资产'][test_date].values[0]:,.2f}")
    
    # 经营资产合计
    print(f"\n经营资产合计: {df_restructured[df_restructured['项目']=='经营资产合计'][test_date].values[0]:,.2f}")
    print(f"  周转性经营投入: {df_restructured[df_restructured['项目']=='周转性经营投入合计'][test_date].values[0]:,.2f}")
    print(f"  长期经营资产: {df_restructured[df_restructured['项目']=='长期经营资产合计'][test_date].values[0]:,.2f}")
    
    # 资产总额
    print(f"\n资产总额: {df_restructured[df_restructured['项目']=='资产总额'][test_date].values[0]:,.2f}")
    
    # 资本总额
    print(f"\n有息债务合计: {df_restructured[df_restructured['项目']=='有息债务合计'][test_date].values[0]:,.2f}")
    print(f"所有者权益合计: {df_restructured[df_restructured['项目']=='所有者权益合计'][test_date].values[0]:,.2f}")
    print(f"资本总额: {df_restructured[df_restructured['项目']=='资本总额'][test_date].values[0]:,.2f}")
