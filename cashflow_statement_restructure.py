"""
现金流量表重构模块
将传统现金流量表重构为现金流量分析表
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging


# ============================================================================
# 字段名映射（现金流量表）
# ============================================================================

CASHFLOW_FIELD_MAPPING = {
    # 经营活动现金流入
    '销售商品、提供劳务收到的现金': '销售收到现金',
    '收到的税费返还': '税费返还',
    '收到其他与经营活动有关的现金': '其他经营收到现金',
    '经营活动现金流入小计': '经营现金流入小计',
    
    # 经营活动现金流出
    '购买商品、接受劳务支付的现金': '购买支付现金',
    '支付给职工以及为职工支付的现金': '职工支付现金',
    '支付的各项税费': '税费支付',
    '支付其他与经营活动有关的现金': '其他经营支付现金',
    '经营活动现金流出小计': '经营现金流出小计',
    
    # 经营活动净额
    '经营活动产生的现金流量净额': '经营现金流净额',
    
    # 非付现成本费用
    '资产减值准备': '资产减值准备',
    '固定资产折旧、油气资产折耗、生产性生物资产折旧': '固定资产折旧',
    '无形资产摊销': '无形资产摊销',
    '长期待摊费用摊销': '长期待摊费用摊销',
    '处置固定资产、无形资产和其他长期资产的损失': '处置长期资产损失',
    '固定资产报废损失': '固定资产报废损失',
    '信用减值损失': '信用减值损失',
    
    # 投资活动现金流入
    '收回投资收到的现金': '收回投资现金',
    '取得投资收益收到的现金': '投资收益现金',
    '处置固定资产、无形资产和其他长期资产收回的现金净额': '处置长期资产现金',
    '处置子公司及其他营业单位收到的现金净额': '处置子公司现金',
    '收到其他与投资活动有关的现金': '其他投资收到现金',
    '投资活动现金流入小计': '投资现金流入小计',
    
    # 投资活动现金流出
    '购建固定资产、无形资产和其他长期资产支付的现金': '购建长期资产现金',
    '投资支付的现金': '投资支付现金',
    '取得子公司及其他营业单位支付的现金净额': '取得子公司现金',
    '支付其他与投资活动有关的现金': '其他投资支付现金',
    '投资活动现金流出小计': '投资现金流出小计',
    
    # 投资活动净额
    '投资活动产生的现金流量净额': '投资现金流净额',
    
    # 筹资活动
    '取得借款收到的现金': '借款收到现金',
    '发行债券收到的现金': '发行债券现金',
    '偿还债务支付的现金': '偿还债务现金',
    '分配股利、利润或偿付利息支付的现金': '分配股利利息现金',
    '筹资活动产生的现金流量净额': '筹资现金流净额',
}


# ============================================================================
# 现金流量表重构函数
# ============================================================================

def restructure_cashflow_statement(
    df_cashflow: pd.DataFrame,
    income_data: pd.DataFrame = None,
    balance_data: pd.DataFrame = None,
    income_restructured: pd.DataFrame = None
) -> pd.DataFrame:
    """
    重构现金流量表:将传统结构转换为现金流量分析表
    
    Args:
        df_cashflow: 原始现金流量表数据
            - 原始格式：每一行是一个报告期，字段名为列（如tushare返回的格式）
            - 转置格式：字段名为行，日期为列（可选）
        income_data: 原始利润表数据,用于获取营业收入、营业总成本
        balance_data: 重构后的资产负债表数据,用于获取长期经营资产
        income_restructured: 重构后的利润表数据,用于获取息前税后经营利润、净利润
        
    Returns:
        重构后的现金流量分析表 DataFrame
    """
    logger = logging.getLogger(__name__)
    
    # 处理重复的列名
    df_cashflow = _clean_duplicate_columns(df_cashflow)
    
    # 确保数据格式正确
    if '字段名' in df_cashflow.columns:
        # 已经是转置格式
        df_data = df_cashflow.set_index('字段名')
        logger.info("输入数据为转置格式")
    elif '项目' in df_cashflow.columns:
        # 已经是转置格式：项目名为第一列（从 main.py 传入）
        df_data = df_cashflow.set_index('项目')
        logger.info("输入数据为转置格式（项目列）")
    elif '报告期' in df_cashflow.columns or 'end_date' in df_cashflow.columns:
        # 原始格式：需要转置
        logger.info("输入数据为原始格式，进行转置...")
        
        # 确定报告期列名
        date_col = '报告期' if '报告期' in df_cashflow.columns else 'end_date'
        
        # 获取数值列（排除非数值列）
        non_numeric_cols = ['TS股票代码', 'ts_code', '公告日期', 'ann_date', '实际公告日期', 'f_ann_date',
                           '报告期', 'end_date', '报表类型', 'report_type', '公司类型', 'comp_type',
                           '报告期类型', 'end_type', '更新标识', 'update_flag']
        numeric_cols = [col for col in df_cashflow.columns if col not in non_numeric_cols]
        
        # 提取数值部分和报告期
        df_work = df_cashflow[[date_col] + numeric_cols].copy()
        
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
        df_data = df_cashflow.copy()
    
    # 标准化字段名
    df_data = _standardize_cashflow_field_names(df_data)
    
    # 获取所有日期列（统一转为字符串，避免 int/str 混用导致匹配失败）
    date_columns = [str(c) for c in df_data.columns.tolist()]
    df_data.columns = date_columns
    
    # 创建重构后的数据结构
    restructured_data = {}
    
    # ========================================================================
    # 1. 自由现金流量分析
    # ========================================================================
    logger.info("计算自由现金流量分析...")
    
    # 从现金流量表获取数据
    sales_cash_received = _safe_get_value(df_data, '销售收到现金', date_columns)
    purchase_cash_paid = _safe_get_value(df_data, '购买支付现金', date_columns)
    employee_cash_paid = _safe_get_value(df_data, '职工支付现金', date_columns)
    operating_cash_flow = _safe_get_value(df_data, '经营现金流净额', date_columns)
    
    # 从利润表获取营业收入和营业总成本
    # 营业总成本 = 营业成本 + 销售费用 + 管理费用 + 研发费用 + 税金及附加
    revenue = pd.Series(0.0, index=date_columns)
    total_cost = pd.Series(0.0, index=date_columns)
    
    if income_data is not None and len(income_data) > 0:
        # 判断利润表数据格式并转置
        if '字段名' in income_data.columns:
            income_df = income_data.set_index('字段名')
        elif '项目' in income_data.columns:
            income_df = income_data.set_index('项目')
        elif '报告期' in income_data.columns or 'end_date' in income_data.columns:
            date_col = '报告期' if '报告期' in income_data.columns else 'end_date'
            non_numeric_cols = ['TS代码', 'ts_code', '公告日期', 'ann_date', '实际公告日期', 'f_ann_date',
                               '报告期', 'end_date', '报表类型', 'report_type', '公司类型', 'comp_type',
                               '报告期类型', 'end_type', '更新标识', 'update_flag']
            numeric_cols = [col for col in income_data.columns if col not in non_numeric_cols]
            df_work = income_data[[date_col] + numeric_cols].copy()
            df_work = df_work.set_index(date_col)
            income_df = df_work.T
            income_df.index.name = '字段名'
        else:
            income_df = None
        
        if income_df is not None:
            # 列名统一转字符串，与 date_columns 类型保持一致
            income_df.columns = income_df.columns.astype(str)
            for col in date_columns:
                if col in income_df.columns:
                    # 获取营业收入
                    if '营业收入' in income_df.index:
                        val = income_df.loc['营业收入', col]
                        if pd.notna(val):
                            revenue[col] = val
                    
                    # 计算营业总成本 = 营业成本 + 销售费用 + 管理费用 + 研发费用 + 税金及附加
                    # 注意：原始数据中字段名为"营业税金及附加"
                    cost_components = ['营业成本', '销售费用', '管理费用', '研发费用', '营业税金及附加']
                    cost_sum = 0
                    for component in cost_components:
                        if component in income_df.index:
                            val = income_df.loc[component, col]
                            if pd.notna(val):
                                cost_sum += val
                    total_cost[col] = cost_sum
    
    restructured_data['销售商品、提供劳务收到的现金'] = sales_cash_received
    restructured_data['营业收入'] = revenue
    
    # 口径一收入现金含量 = 销售收到现金 / 营业收入
    sales_cash_ratio = sales_cash_received / revenue.replace(0, np.nan)
    restructured_data['口径一收入现金含量'] = sales_cash_ratio
    
    restructured_data['购买商品、接收劳务支付的现金'] = purchase_cash_paid
    restructured_data['支付给职工及为职工支付的现金'] = employee_cash_paid
    restructured_data['营业总成本'] = total_cost
    
    # 成本费用付现率（严格按照文档公式）
    # 成本费用付现率 = (购买支付现金 / 1.17 + 职工支付现金) / 营业总成本
    # 注意:购买支付现金包含增值税,需要除以1.17还原为不含税金额(17%增值税率)
    cost_cash_ratio = (purchase_cash_paid / 1.17 + employee_cash_paid) / total_cost.replace(0, np.nan)
    restructured_data['成本费用付现率'] = cost_cash_ratio
    
    restructured_data['经营活动产生的现金流量净额'] = operating_cash_flow
    
    # 从重构后的利润表获取息前税后经营利润和净利润
    nopat_operating = pd.Series(0.0, index=date_columns)
    net_profit = pd.Series(0.0, index=date_columns)
    
    if income_restructured is not None and '项目' in income_restructured.columns:
        for col in date_columns:
            if col in income_restructured.columns:
                # 息前税后经营利润
                nopat_row = income_restructured[income_restructured['项目'] == '息前税后经营利润']
                if len(nopat_row) > 0:
                    val = nopat_row[col].values[0]
                    if pd.notna(val):
                        nopat_operating[col] = val
                
                # 净利润
                profit_row = income_restructured[income_restructured['项目'] == '净利润']
                if len(profit_row) > 0:
                    val = profit_row[col].values[0]
                    if pd.notna(val):
                        net_profit[col] = val
    
    restructured_data['息前税后经营利润'] = nopat_operating
    
    # 息前税后经营利润现金含量 = 经营现金流 / 息前税后经营利润
    nopat_cash_ratio = operating_cash_flow / nopat_operating.replace(0, np.nan)
    restructured_data['息前税后经营利润现金含量'] = nopat_cash_ratio
    
    restructured_data['净利润'] = net_profit
    
    # 净利润现金含量 = 经营现金流 / 净利润
    profit_cash_ratio = operating_cash_flow / net_profit.replace(0, np.nan)
    restructured_data['净利润现金含量'] = profit_cash_ratio
    
    # ========================================================================
    # 2. 经营活动产生的现金流量净额分析
    # ========================================================================
    logger.info("计算经营活动现金流净额分析...")
    
    # 获取非付现成本费用
    asset_impairment = _safe_get_value(df_data, '资产减值准备', date_columns)
    depreciation = _safe_get_value(df_data, '固定资产折旧', date_columns)
    amortization = _safe_get_value(df_data, '无形资产摊销', date_columns)
    longterm_amortization = _safe_get_value(df_data, '长期待摊费用摊销', date_columns)
    disposal_loss = _safe_get_value(df_data, '处置长期资产损失', date_columns)
    scrap_loss = _safe_get_value(df_data, '固定资产报废损失', date_columns)
    credit_impairment = _safe_get_value(df_data, '信用减值损失', date_columns)
    
    # 从利润表获取资产处置收益(作为处置长期资产损失的补充)
    # 注意:现金流量表中的"处置长期资产损失"字段通常为空,需要从利润表获取
    if income_data is not None and ('字段名' in income_data.columns or '项目' in income_data.columns):
        _field_col = '字段名' if '字段名' in income_data.columns else '项目'
        income_df = income_data.set_index(_field_col)
        income_df.columns = income_df.columns.astype(str)
        for col in date_columns:
            if col in income_df.columns:
                # 资产处置收益(负数为损失)
                if '资产处置收益' in income_df.index:
                    val = income_df.loc['资产处置收益', col]
                    if pd.notna(val) and val < 0:
                        # 负数的资产处置收益表示损失,取绝对值
                        if disposal_loss[col] == 0:
                            disposal_loss[col] = abs(val)
    
    restructured_data['加：资产减值准备'] = asset_impairment
    restructured_data['固定资产折旧、油气资产折耗、生产性生物资产折旧'] = depreciation
    restructured_data['无形资产摊销'] = amortization
    restructured_data['长期待摊费用摊销'] = longterm_amortization
    restructured_data['处置固定资产、无形资产和其他长期资产的损失'] = disposal_loss
    restructured_data['固定资产报废损失'] = scrap_loss
    
    # 非付现成本费用 = 资产减值准备 + 折旧 + 摊销 + 处置损失 + 报废损失
    non_cash_costs = (asset_impairment.abs() + depreciation.abs() + amortization.abs() 
                     + longterm_amortization.abs() + disposal_loss.abs() + scrap_loss.abs()
                     + credit_impairment.abs())
    restructured_data['非付现成本费用'] = non_cash_costs
    
    # 非付现成本费用比经营活动产生的现金流量净额
    non_cash_costs_ratio = non_cash_costs / operating_cash_flow.replace(0, np.nan)
    restructured_data['非付现成本费用比经营活动产生的现金流量净额'] = non_cash_costs_ratio
    
    # 经营资产自由现金流量 = 经营活动现金流净额 - 非付现成本费用
    operating_asset_free_cashflow = operating_cash_flow - non_cash_costs
    restructured_data['经营资产自由现金流量'] = operating_asset_free_cashflow
    
    # 注：原文档中"净利润计算得到的自由现金流"未定义计算公式，暂不输出
    
    # ========================================================================
    # 3. 投资活动产生的现金流量分析
    # ========================================================================
    logger.info("计算投资活动现金流量分析...")
    
    # 投资活动现金流入
    invest_recover_cash = _safe_get_value(df_data, '收回投资现金', date_columns)
    invest_income_cash = _safe_get_value(df_data, '投资收益现金', date_columns)
    dispose_asset_cash = _safe_get_value(df_data, '处置长期资产现金', date_columns)
    dispose_subsidiary_cash = _safe_get_value(df_data, '处置子公司现金', date_columns)
    other_invest_in_cash = _safe_get_value(df_data, '其他投资收到现金', date_columns)
    invest_inflow_subtotal = _safe_get_value(df_data, '投资现金流入小计', date_columns)
    
    restructured_data['收回投资收到的现金'] = invest_recover_cash
    restructured_data['取得投资收益所收到的现金'] = invest_income_cash
    restructured_data['处置固定资产、无形资产及其他长期资产收到的现金'] = dispose_asset_cash
    restructured_data['处置子公司、合营联营企业及其他营业单位收到的现金净额'] = dispose_subsidiary_cash
    restructured_data['收到的其他与投资活动相关的现金'] = other_invest_in_cash
    restructured_data['投资活动现金流入小计'] = invest_inflow_subtotal
    
    # 投资活动现金流出
    purchase_asset_cash = _safe_get_value(df_data, '购建长期资产现金', date_columns)
    invest_pay_cash = _safe_get_value(df_data, '投资支付现金', date_columns)
    acquire_subsidiary_cash = _safe_get_value(df_data, '取得子公司现金', date_columns)
    other_invest_out_cash = _safe_get_value(df_data, '其他投资支付现金', date_columns)
    invest_outflow_subtotal = _safe_get_value(df_data, '投资现金流出小计', date_columns)
    
    restructured_data['购建固定资产、无形资产及其他长期资产所支付的现金'] = purchase_asset_cash
    restructured_data['投资所支付的现金'] = invest_pay_cash
    restructured_data['取得子公司、合营联营企业及其他营业单位支付的现金净额'] = acquire_subsidiary_cash
    restructured_data['支付的其他与投资活动有关的现金'] = other_invest_out_cash
    restructured_data['投资活动现金流出小计'] = invest_outflow_subtotal
    
    # 投资活动产生的现金流净额 = 投资流入小计 - 投资流出小计
    invest_cash_flow = _safe_get_value(df_data, '投资现金流净额', date_columns)
    restructured_data['投资活动产生的现金流净额'] = invest_cash_flow
    
    # ========================================================================
    # 4. 长期经营资产投资活动现金流量分析
    # ========================================================================
    logger.info("计算长期经营资产投资活动现金流量分析...")
    
    restructured_data['处置固定资产、无形资产及其他长期资产收到的现金'] = dispose_asset_cash
    restructured_data['购建固定资产、无形资产及其他长期资产所支付的现金'] = purchase_asset_cash
    
    # 长期经营资产净投资额 = 购建支付 - 处置收到
    longterm_asset_net_invest = purchase_asset_cash - dispose_asset_cash
    restructured_data['长期经营资产净投资额'] = longterm_asset_net_invest
    
    # 获取折旧、摊销、处置损失、报废损失
    restructured_data['固定资产折旧、油气资产折耗、生产性生物资产折旧'] = depreciation
    restructured_data['无形资产摊销'] = amortization
    restructured_data['长期待摊费用摊销'] = longterm_amortization
    restructured_data['处置固定资产、无形资产和其他长期资产的损失'] = disposal_loss
    restructured_data['固定资产报废损失'] = scrap_loss
    
    # 长期经营资产扩张性资本支出 = 净投资额 - 折旧 - 摊销 - 处置损失 - 报废损失
    expansion_capex = (longterm_asset_net_invest - depreciation.abs() - amortization.abs() 
                      - longterm_amortization.abs() - disposal_loss.abs() - scrap_loss.abs())
    restructured_data['长期经营资产扩张性资本支出'] = expansion_capex
    
    # 从资产负债表获取长期经营资产合计（期末值）
    longterm_operating_assets = pd.Series(0.0, index=date_columns)
    # 从资产负债表获取长期经营资产合计（期初值，即上一个报告期的期末值）
    longterm_operating_assets_begin = pd.Series(0.0, index=date_columns)
    
    if balance_data is not None and '项目' in balance_data.columns:
        # 确保资产负债表的列名都是字符串类型（避免整数列名导致的匹配失败）
        balance_data = balance_data.copy()
        balance_data.columns = [str(col) for col in balance_data.columns]
        
        asset_row = balance_data[balance_data['项目'] == '长期经营资产合计']
        if len(asset_row) > 0:
            # 按日期升序排列（从旧到新）
            sorted_dates = sorted(date_columns)
            
            # 构建年报数据字典（只包含1231结尾的日期）
            annual_assets = {}
            for col in sorted_dates:
                if col in asset_row.columns:
                    val = asset_row[col].values[0]
                    if pd.notna(val):
                        longterm_operating_assets[col] = val  # 期末值
                        if col.endswith('1231'):
                            annual_assets[col] = val
            
            # 计算期初长期资产
            for col in sorted_dates:
                if col in asset_row.columns:
                    val = asset_row[col].values[0]
                    if pd.notna(val):
                        # 如果是年报（1231结尾），期初 = 上一年年报
                        if col.endswith('1231'):
                            year = int(col[:4])
                            prev_year_date = f"{year-1}1231"
                            if prev_year_date in annual_assets:
                                longterm_operating_assets_begin[col] = annual_assets[prev_year_date]
                        else:
                            # 如果是季报，期初 = 同年上一季度或上年年报
                            year = int(col[:4])
                            month_day = col[4:]
                            
                            # 找到上一个报告期
                            if month_day == '0331':
                                # Q1的期初 = 上年年报
                                prev_date = f"{year-1}1231"
                            elif month_day == '0630':
                                # Q2的期初 = 当年Q1
                                prev_date = f"{year}0331"
                            elif month_day == '0930':
                                # Q3的期初 = 当年Q2
                                prev_date = f"{year}0630"
                            else:
                                prev_date = None
                            
                            if prev_date and prev_date in asset_row.columns:
                                prev_val = asset_row[prev_date].values[0]
                                if pd.notna(prev_val):
                                    longterm_operating_assets_begin[col] = prev_val
    
    restructured_data['长期经营资产合计'] = longterm_operating_assets
    
    # 长期经营资产扩张性资本支出比例 = 扩张性资本支出 / 期初长期经营资产
    expansion_capex_ratio = expansion_capex / longterm_operating_assets_begin.replace(0, np.nan)
    restructured_data['长期经营资产扩张性资本支出比例'] = expansion_capex_ratio
    
    # ========================================================================
    # 5. 并购活动现金流量分析
    # ========================================================================
    logger.info("计算并购活动现金流量分析...")
    
    restructured_data['处置子公司、合营联营企业及其他营业单位收到的现金净额'] = dispose_subsidiary_cash
    restructured_data['取得子公司、合营联营企业及其他营业单位支付的现金净额'] = acquire_subsidiary_cash
    
    # 净合并额 = 取得支付 - 处置收到
    net_merger = acquire_subsidiary_cash - dispose_subsidiary_cash
    restructured_data['净合并额'] = net_merger
    
    # ========================================================================
    # 6. 资本支出分析
    # ========================================================================
    logger.info("计算资本支出分析...")
    
    restructured_data['长期经营资产净投资额'] = longterm_asset_net_invest
    restructured_data['长期经营资产扩张性资本支出'] = expansion_capex
    restructured_data['净合并额'] = net_merger
    
    # 资本支出总额 = 长期经营资产净投资额 + 净合并额
    total_capex = longterm_asset_net_invest + net_merger
    restructured_data['资本支出总额'] = total_capex
    
    # 扩张性资本支出 = 长期经营资产扩张性资本支出 + 净合并额
    total_expansion_capex = expansion_capex + net_merger
    restructured_data['扩张性资本支出'] = total_expansion_capex
    
    # 扩张性资本支出占长期资产期初净额的比例
    expansion_capex_ratio_total = total_expansion_capex / longterm_operating_assets_begin.replace(0, np.nan)
    restructured_data['扩张性资本支出占长期资产期初净额的比例'] = expansion_capex_ratio_total
    
    # ========================================================================
    # 7. 债务筹资现金流量分析
    # ========================================================================
    logger.info("计算债务筹资现金流量分析...")
    
    # 获取筹资活动数据
    borrow_cash = _safe_get_value(df_data, '借款收到现金', date_columns)
    bond_cash = _safe_get_value(df_data, '发行债券现金', date_columns)
    repay_debt_cash = _safe_get_value(df_data, '偿还债务现金', date_columns)
    dividend_interest_cash = _safe_get_value(df_data, '分配股利利息现金', date_columns)
    
    restructured_data['取得借款收到的现金'] = borrow_cash
    restructured_data['发行债券收到的现金'] = bond_cash
    restructured_data['偿付债务支付的现金'] = repay_debt_cash
    
    # 偿付利息支付的现金
    # 计算公式：偿付利息支付的现金 = 利息费用 + (应付利息的增加)
    #         = 利息费用 + (期末应付利息 - 期初应付利息)
    # 注意:需要从利润表获取利息费用，从资产负债表获取应付利息
    
    interest_payment = pd.Series(0.0, index=date_columns)
    
    # 获取利息费用（从利润表）
    interest_expense = pd.Series(0.0, index=date_columns)
    if income_data is not None and len(income_data) > 0:
        # 判断利润表数据格式并转置（与营业总成本获取逻辑相同）
        if '字段名' in income_data.columns:
            income_df_for_interest = income_data.set_index('字段名')
        elif '项目' in income_data.columns:
            income_df_for_interest = income_data.set_index('项目')
        elif '报告期' in income_data.columns or 'end_date' in income_data.columns:
            date_col = '报告期' if '报告期' in income_data.columns else 'end_date'
            non_numeric_cols = ['TS代码', 'ts_code', '公告日期', 'ann_date', '实际公告日期', 'f_ann_date',
                               '报告期', 'end_date', '报表类型', 'report_type', '公司类型', 'comp_type',
                               '报告期类型', 'end_type', '更新标识', 'update_flag']
            numeric_cols = [col for col in income_data.columns if col not in non_numeric_cols]
            df_work = income_data[[date_col] + numeric_cols].copy()
            df_work = df_work.set_index(date_col)
            income_df_for_interest = df_work.T
            income_df_for_interest.index.name = '字段名'
        else:
            income_df_for_interest = None
        
        if income_df_for_interest is not None:
            income_df_for_interest.columns = income_df_for_interest.columns.astype(str)
        
        if income_df_for_interest is not None:
            for col in date_columns:
                if col in income_df_for_interest.columns:
                    # 财务费用:利息费用
                    if '财务费用:利息费用' in income_df_for_interest.index:
                        val = income_df_for_interest.loc['财务费用:利息费用', col]
                        if pd.notna(val):
                            interest_expense[col] = abs(val)
    
    # 获取应付利息变动（从资产负债表）
    # 应付利息的增加 = 期末应付利息 - 期初应付利息
    # 注意：对于年报（12月31日），期初应为上一年年报的应付利息
    interest_payable_increase = pd.Series(0.0, index=date_columns)
    interest_payable_begin = pd.Series(0.0, index=date_columns)  # 期初应付利息
    interest_payable_end = pd.Series(0.0, index=date_columns)    # 期末应付利息（当前报告期）
    
    if balance_data is not None and '项目' in balance_data.columns:
        # 获取应付利息行
        interest_payable_row = balance_data[balance_data['项目'] == '应付利息']
        if len(interest_payable_row) > 0:
            # 按日期升序排列（从旧到新）
            sorted_dates = sorted(date_columns)
            
            # 构建日期到应付利息的映射
            date_to_interest = {}
            for col in sorted_dates:
                if col in interest_payable_row.columns:
                    val = interest_payable_row[col].values[0]
                    if pd.notna(val):
                        date_to_interest[col] = val
            
            # 计算每个报告期的应付利息变动
            for col in sorted_dates:
                if col in date_to_interest:
                    current_interest_payable = date_to_interest[col]
                    interest_payable_end[col] = current_interest_payable
                    
                    # 判断是否为年报（12月31日）
                    if col.endswith('1231'):
                        # 年报：期初 = 上一年年报
                        year = int(col[:4])
                        prev_year_col = f"{year-1}1231"
                        if prev_year_col in date_to_interest:
                            prev_interest_payable = date_to_interest[prev_year_col]
                            interest_payable_begin[col] = prev_interest_payable
                            interest_payable_increase[col] = current_interest_payable - prev_interest_payable
                    else:
                        # 季报：期初 = 上一个报告期
                        # 找到上一个报告期
                        col_idx = sorted_dates.index(col)
                        for prev_idx in range(col_idx - 1, -1, -1):
                            prev_col = sorted_dates[prev_idx]
                            if prev_col in date_to_interest:
                                prev_interest_payable = date_to_interest[prev_col]
                                interest_payable_begin[col] = prev_interest_payable
                                interest_payable_increase[col] = current_interest_payable - prev_interest_payable
                                break
    
    # 偿付利息支付的现金 = 利息费用 + 应付利息的增加
    interest_payment = interest_expense + interest_payable_increase
    
    # 添加辅助信息（便于验证）
    restructured_data['(辅助)利息费用'] = interest_expense
    restructured_data['(辅助)应付利息期初'] = interest_payable_begin
    restructured_data['(辅助)应付利息期末'] = interest_payable_end
    restructured_data['(辅助)应付利息增加'] = interest_payable_increase
    restructured_data['偿付利息支付的现金'] = interest_payment
    
    # 债务筹资净额 = 取得借款 + 发行债券 - 偿付债务 - 偿付利息
    debt_financing_net = borrow_cash + bond_cash - repay_debt_cash - interest_payment
    restructured_data['债务筹资净额'] = debt_financing_net
    
    # ========================================================================
    # 创建重构后的DataFrame
    # ========================================================================
    
    # 定义输出顺序
    output_order = [
        # 自由现金流量分析
        '销售商品、提供劳务收到的现金',
        '营业收入',
        '口径一收入现金含量',
        '购买商品、接收劳务支付的现金',
        '支付给职工及为职工支付的现金',
        '营业总成本',
        '成本费用付现率',
        '经营活动产生的现金流量净额',
        '息前税后经营利润',
        '息前税后经营利润现金含量',
        '净利润',
        '净利润现金含量',
        
        # 经营活动现金流净额分析
        '经营活动产生的现金流量净额',
        '加：资产减值准备',
        '固定资产折旧、油气资产折耗、生产性生物资产折旧',
        '无形资产摊销',
        '长期待摊费用摊销',
        '处置固定资产、无形资产和其他长期资产的损失',
        '固定资产报废损失',
        '非付现成本费用',
        '非付现成本费用比经营活动产生的现金流量净额',
        '经营资产自由现金流量',
        
        # 投资活动现金流量分析
        '收回投资收到的现金',
        '取得投资收益所收到的现金',
        '处置固定资产、无形资产及其他长期资产收到的现金',
        '处置子公司、合营联营企业及其他营业单位收到的现金净额',
        '收到的其他与投资活动相关的现金',
        '投资活动现金流入小计',
        '购建固定资产、无形资产及其他长期资产所支付的现金',
        '投资所支付的现金',
        '取得子公司、合营联营企业及其他营业单位支付的现金净额',
        '支付的其他与投资活动有关的现金',
        '投资活动现金流出小计',
        '投资活动产生的现金流净额',
        
        # 长期经营资产投资活动现金流量分析
        '处置固定资产、无形资产及其他长期资产收到的现金',
        '购建固定资产、无形资产及其他长期资产所支付的现金',
        '长期经营资产净投资额',
        '固定资产折旧、油气资产折耗、生产性生物资产折旧',
        '无形资产摊销',
        '长期待摊费用摊销',
        '处置固定资产、无形资产和其他长期资产的损失',
        '固定资产报废损失',
        '长期经营资产扩张性资本支出',
        '长期经营资产合计',
        '长期经营资产扩张性资本支出比例',
        '扩张性资本支出',
        '扩张性资本支出占长期资产期初净额的比例',
        
        # 并购活动现金流量分析
        '处置子公司、合营联营企业及其他营业单位收到的现金净额',
        '取得子公司、合营联营企业及其他营业单位支付的现金净额',
        '净合并额',
        
        # 资本支出分析
        '长期经营资产净投资额',
        '长期经营资产扩张性资本支出',
        '净合并额',
        '资本支出总额',
        '扩张性资本支出',
        
        # 债务筹资现金流量分析
        '取得借款收到的现金',
        '发行债券收到的现金',
        '偿付债务支付的现金',
        '(辅助)利息费用',
        '(辅助)应付利息期初',
        '(辅助)应付利息期末',
        '(辅助)应付利息增加',
        '偿付利息支付的现金',
        '债务筹资净额',
    ]
    
    # 创建DataFrame
    df_result = pd.DataFrame(restructured_data).T
    
    # 按照预定义顺序排列
    available_items = [item for item in output_order if item in df_result.index]
    df_result = df_result.loc[available_items]
    
    # 重置索引
    df_result = df_result.reset_index()
    df_result = df_result.rename(columns={'index': '项目'})
    
    logger.info(f"现金流量表重构完成,共 {len(df_result)} 个项目")
    
    return df_result


# ============================================================================
# 辅助函数
# ============================================================================

def _clean_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    清理重复的列名(如 20250930, 20250930.1 等)
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


def _standardize_cashflow_field_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    标准化现金流量表字段名
    """
    new_index = []
    for idx in df.index:
        if idx in CASHFLOW_FIELD_MAPPING:
            new_index.append(CASHFLOW_FIELD_MAPPING[idx])
        else:
            new_index.append(idx)
    
    df.index = new_index
    return df


def _safe_get_value(df: pd.DataFrame, 
                    field_name: str, 
                    date_columns: List[str]) -> pd.Series:
    """
    安全获取字段值
    
    处理重复索引的情况:取第一个非NaN值
    """
    if field_name in df.index:
        val = df.loc[field_name]
        
        # 处理重复索引的情况
        if isinstance(val, pd.DataFrame):
            # 对于每个日期列,取第一个非NaN值
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
    cashflow_file = 'data/603345.SH_cashflow.csv'
    income_file = 'data/603345.SH_income.csv'
    
    df_cashflow = pd.read_csv(cashflow_file, encoding='utf-8-sig')
    df_income = pd.read_csv(income_file, encoding='utf-8-sig')
    
    print("原始现金流量表形状:", df_cashflow.shape)
    
    # 重构现金流量表
    df_restructured = restructure_cashflow_statement(
        df_cashflow,
        income_data=df_income
    )
    
    print("\n重构后数据形状:", df_restructured.shape)
    print("\n重构后数据:")
    print(df_restructured.to_string())
    
    # 保存结果
    output_file = 'data/603345.SH_cashflow_restructured.csv'
    df_restructured.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n重构后的现金流量表已保存到: {output_file}")
