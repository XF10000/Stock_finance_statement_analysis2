# Tushare 财务报表字段文档

本文档包含了 Tushare API 提供的财务报表字段信息，包括资产负债表、利润表和现金流量表的所有字段。

**最后更新**: 2026-03-14
**更新内容**: 修正了现金流量表补充资料部分的字段映射错误，所有映射现已与 Tushare API 实际返回完全一致。

## 重要说明

### 字段获取策略

**本项目获取所有字段，无论默认显示是 Y 还是 N。**

Tushare API 的输出参数中有一个"默认显示"列，标记为 Y 或 N：
- **Y (默认显示)**：接口默认会返回该字段
- **N (隐藏字段)**：接口默认不会返回该字段，需要在调用时通过 `fields` 参数手动指定

**本项目的设计原则：**
1. **完整性**：获取所有可用字段，不遗漏任何数据
2. **一致性**：所有财务报表（资产负债表、利润表、现金流量表）都采用相同的策略
3. **可扩展性**：当 Tushare 新增字段时，能够方便地添加到获取列表中

### 技术实现方法

#### 问题背景

Tushare API 在调用财务报表接口时，默认只返回"默认显示"列为 Y 的字段。许多重要字段（如 `receiv_financing` 应收款项融资、`contract_assets` 合同资产等）默认显示为 N，如果不显式指定，这些字段将不会被返回。

#### 解决方案

**必须通过 `fields` 参数显式指定所有需要获取的字段**，包括默认显示为 Y 和 N 的所有字段。

#### 代码实现

在 `data_provider/tushare_client.py` 中，每个财务报表获取方法都显式指定了完整的字段列表，并且实现了分页获取和上市日期过滤：

```python
def get_balancesheet(self, ts_code: str, start_date: Optional[str] = None, 
                     end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    获取单个股票的资产负债表数据
    """
    # 构建参数 - 包含所有需要的字段，包括默认显示为N的隐藏字段
    fields = "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,end_type,"
            "total_share,cap_rese,undistr_porfit,surplus_rese,special_rese,"
            "money_cap,trad_asset,notes_receiv,accounts_receiv,receiv_financing,"
            # ... 省略其他字段 ...
            "contract_assets,contract_liab,accounts_receiv_bill,accounts_pay,"
            "oth_rcv_total,fix_assets_total,cip_total,oth_pay_total,long_pay_total,"
            "debt_invest,oth_debt_invest,update_flag"
    
    params = {
        "ts_code": ts_code,
        "fields": fields
    }
    
    # 如果没有指定开始日期，使用分页获取全部数据
    if not start_date:
        df = self._make_request_with_pagination(self.pro.balancesheet, **params)
    else:
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        df = self._make_request(self.pro.balancesheet, **params)
    
    # 如果没有指定开始日期，需要用上市日期过滤掉上市前的无效数据
    if not start_date:
        list_date = self.get_stock_list_date(ts_code)
        if list_date:
            original_count = len(df)
            df = df[df['end_date'] >= list_date]
            if len(df) < original_count:
                self.logger.info(f"{ts_code}: 过滤掉 {original_count - len(df)} 条上市前数据，上市日期: {list_date}")

    return df
```

#### 关键要点

1. **不要省略 `fields` 参数**：如果不指定 `fields`，API 只返回默认显示为 Y 的字段
2. **字段列表必须完整**：需要根据 Tushare 官方文档，整理所有可用字段（包括 Y 和 N）
3. **数据库模型同步更新**：获取的字段必须在 `models.py` 中有对应的列定义
4. **定期检查字段更新**：Tushare 可能新增字段，需要定期对照官方文档更新

#### 字段统计

| 报表类型 | 字段总数 | 默认显示Y | 隐藏字段N |
|---------|---------|----------|----------|
| 财务指标表 | 180 | ~120 | ~60 |
| 资产负债表 | 156 | ~130 | ~26 |
| 利润表 | 94 | ~88 | ~6 |
| 现金流量表 | 99 | ~95 | ~4 |
| **合计** | **529** | - | - |

#### 常见隐藏字段示例

以下是部分重要的隐藏字段（默认显示为 N）：

**财务指标表：**
- `invturn_days` - 存货周转天数
- `arturn_days` - 应收账款周转天数
- `inv_turn` - 存货周转率
- `valuechange_income` - 价值变动净收益
- `daa` - 折旧与摊销
- `roe_avg` - 平均净资产收益率(增发条件)
- `dtprofit_to_profit` - 扣除非经常损益后的净利润/净利润
- `rd_exp` - 研发费用

**资产负债表：**
- `receiv_financing` - 应收款项融资
- `contract_assets` - 合同资产
- `contract_liab` - 合同负债
- `debt_invest` - 债权投资
- `oth_eqt_tools` - 其他权益工具
- `hfs_assets` - 持有待售资产

**利润表：**
- `credit_impa_loss` - 信用减值损失
- `oth_income` - 其他收益

**现金流量表：**
- `credit_impa_loss` - 信用减值损失

#### 参考文档

- Tushare 财务指标表接口：https://tushare.pro/document/2?doc_id=79
- Tushare 资产负债表接口：https://tushare.pro/document/2?doc_id=36
- Tushare 利润表接口：https://tushare.pro/document/2?doc_id=33
- Tushare 现金流量表接口：https://tushare.pro/document/2?doc_id=44

## 0. 财务指标表 (fina_indicator)

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
|------|------|------|------|
| ts_code | str | Y | TS股票代码 |
| ann_date | str | N | 公告日期 |
| start_date | str | N | 报告期开始日期 |
| end_date | str | N | 报告期结束日期 |
| period | str | N | 报告期(每个季度最后一天的日期) |

### 输出参数（约180个字段）

#### 基础信息
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| ts_code | str | Y | TS代码 |
| ann_date | str | Y | 公告日期 |
| end_date | str | Y | 报告期 |

#### 每股指标
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| eps | float | Y | 基本每股收益 |
| dt_eps | float | Y | 稀释每股收益 |
| total_revenue_ps | float | Y | 每股营业总收入 |
| revenue_ps | float | Y | 每股营业收入 |
| capital_rese_ps | float | Y | 每股资本公积 |
| surplus_rese_ps | float | Y | 每股盈余公积 |
| undist_profit_ps | float | Y | 每股未分配利润 |
| diluted2_eps | float | Y | 期末摊薄每股收益 |
| bps | float | Y | 每股净资产 |
| ocfps | float | Y | 每股经营活动产生的现金流量净额 |
| retainedps | float | Y | 每股留存收益 |
| cfps | float | Y | 每股现金流量净额 |
| ebit_ps | float | Y | 每股息税前利润 |
| fcff_ps | float | Y | 每股企业自由现金流量 |
| fcfe_ps | float | Y | 每股股东自由现金流量 |

#### 盈利能力
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| roe | float | Y | 净资产收益率 |
| roe_waa | float | Y | 加权平均净资产收益率 |
| roe_dt | float | Y | 净资产收益率(扣除非经常损益) |
| roa | float | Y | 总资产报酬率 |
| npta | float | Y | 总资产净利润 |
| roic | float | Y | 投入资本回报率 |
| roe_yearly | float | Y | 年化净资产收益率 |
| roa2_yearly | float | Y | 年化总资产报酬率 |
| roe_avg | float | N | 平均净资产收益率(增发条件) |
| roa_yearly | float | Y | 年化总资产净利率 |
| roa_dp | float | Y | 总资产净利率(杜邦分析) |
| roic_yearly | float | N | 年化投入资本回报率 |

#### 营运能力
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| ar_turn | float | Y | 应收账款周转率 |
| inv_turn | float | N | 存货周转率 |
| ca_turn | float | Y | 流动资产周转率 |
| fa_turn | float | Y | 固定资产周转率 |
| assets_turn | float | Y | 总资产周转率 |
| invturn_days | float | N | 存货周转天数 |
| arturn_days | float | N | 应收账款周转天数 |
| turn_days | float | Y | 营业周期 |
| total_fa_trun | float | N | 固定资产合计周转率 |

#### 偿债能力
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| current_ratio | float | Y | 流动比率 |
| quick_ratio | float | Y | 速动比率 |
| cash_ratio | float | Y | 保守速动比率 |
| debt_to_assets | float | Y | 资产负债率 |
| assets_to_eqt | float | Y | 权益乘数 |
| dp_assets_to_eqt | float | Y | 权益乘数(杜邦分析) |
| debt_to_eqt | float | Y | 产权比率 |
| eqt_to_debt | float | Y | 归属于母公司的股东权益/负债合计 |
| eqt_to_interestdebt | float | Y | 归属于母公司的股东权益/带息债务 |

#### 利润率
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| netprofit_margin | float | Y | 销售净利率 |
| grossprofit_margin | float | Y | 销售毛利率 |
| gross_margin | float | Y | 毛利 |
| cogs_of_sales | float | Y | 销售成本率 |
| expense_of_sales | float | Y | 销售期间费用率 |
| profit_to_gr | float | Y | 净利润/营业总收入 |
| profit_to_op | float | Y | 利润总额／营业收入 |

#### 成长能力
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| basic_eps_yoy | float | Y | 基本每股收益同比增长率(%) |
| dt_eps_yoy | float | Y | 稀释每股收益同比增长率(%) |
| cfps_yoy | float | Y | 每股经营活动产生的现金流量净额同比增长率(%) |
| op_yoy | float | Y | 营业利润同比增长率(%) |
| ebt_yoy | float | Y | 利润总额同比增长率(%) |
| netprofit_yoy | float | Y | 归属母公司股东的净利润同比增长率(%) |
| dt_netprofit_yoy | float | Y | 归属母公司股东的净利润-扣除非经常损益同比增长率(%) |
| ocf_yoy | float | Y | 经营活动产生的现金流量净额同比增长率(%) |
| roe_yoy | float | Y | 净资产收益率(摊薄)同比增长率(%) |
| bps_yoy | float | Y | 每股净资产相对年初增长率(%) |
| assets_yoy | float | Y | 资产总计相对年初增长率(%) |
| eqt_yoy | float | Y | 归属母公司的股东权益相对年初增长率(%) |
| tr_yoy | float | Y | 营业总收入同比增长率(%) |
| or_yoy | float | Y | 营业收入同比增长率(%) |
| equity_yoy | float | Y | 净资产同比增长率 |

#### 单季度指标
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| q_roe | float | Y | 净资产收益率(单季度) |
| q_dt_roe | float | Y | 净资产单季度收益率(扣除非经常损益) |
| q_npta | float | Y | 总资产净利润(单季度) |
| q_sales_yoy | float | Y | 营业收入同比增长率(%)(单季度) |
| q_sales_qoq | float | N | 营业收入环比增长率(%)(单季度) |
| q_op_yoy | float | N | 营业利润同比增长率(%)(单季度) |
| q_op_qoq | float | Y | 营业利润环比增长率(%)(单季度) |
| q_profit_yoy | float | N | 净利润同比增长率(%)(单季度) |
| q_profit_qoq | float | N | 净利润环比增长率(%)(单季度) |
| q_netprofit_yoy | float | N | 归属母公司股东的净利润同比增长率(%)(单季度) |
| q_netprofit_qoq | float | N | 归属母公司股东的净利润环比增长率(%)(单季度) |

#### 其他重要指标
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| ebit | float | Y | 息税前利润 |
| ebitda | float | Y | 息税折旧摊销前利润 |
| fcff | float | Y | 企业自由现金流量 |
| fcfe | float | Y | 股权自由现金流量 |
| working_capital | float | Y | 营运资金 |
| networking_capital | float | Y | 营运流动资本 |
| tangible_asset | float | Y | 有形资产 |
| rd_exp | float | N | 研发费用 |
| profit_dedt | float | Y | 扣除非经常性损益后的净利润 |
| extra_item | float | Y | 非经常性损益 |
| update_flag | str | N | 更新标识 |

## 1. 资产负债表 (balancesheet)

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
|------|------|------|------|
| ts_code | str | Y | 股票代码 |
| ann_date | str | N | 公告日期(YYYYMMDD格式) |
| start_date | str | N | 公告日开始日期 |
| end_date | str | N | 公告日结束日期 |
| period | str | N | 报告期(每个季度最后一天的日期) |
| report_type | str | N | 报告类型 |
| comp_type | str | N | 公司类型：1一般工商业 2银行 3保险 4证券 |

### 输出参数
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| ts_code | str | Y | TS股票代码 |
| ann_date | str | Y | 公告日期 |
| f_ann_date | str | Y | 实际公告日期 |
| end_date | str | Y | 报告期 |
| report_type | str | Y | 报表类型 |
| comp_type | str | Y | 公司类型(1一般工商业2银行3保险4证券) |
| end_type | str | Y | 报告期类型 |
| total_share | float | Y | 期末总股本 |
| cap_rese | float | Y | 资本公积金 |
| undistr_porfit | float | Y | 未分配利润 |
| surplus_rese | float | Y | 盈余公积金 |
| special_rese | float | Y | 专项储备 |
| money_cap | float | Y | 货币资金 |
| trad_asset | float | Y | 交易性金融资产 |
| notes_receiv | float | Y | 应收票据 |
| accounts_receiv | float | Y | 应收账款 |
| receiv_financing | float | N | 应收款项融资 |
| oth_receiv | float | Y | 其他应收款 |
| prepayment | float | Y | 预付款项 |
| div_receiv | float | Y | 应收股利 |
| int_receiv | float | Y | 应收利息 |
| inventories | float | Y | 存货 |
| amor_exp | float | Y | 待摊费用 |
| nca_within_1y | float | Y | 一年内到期的非流动资产 |
| sett_rsrv | float | Y | 结算备付金 |
| loanto_oth_bank_fi | float | Y | 拆出资金 |
| premium_receiv | float | Y | 应收保费 |
| reinsur_receiv | float | Y | 应收分保账款 |
| reinsur_res_receiv | float | Y | 应收分保合同准备金 |
| pur_resale_fa | float | Y | 买入返售金融资产 |
| oth_cur_assets | float | Y | 其他流动资产 |
| total_cur_assets | float | Y | 流动资产合计 |
| fa_avail_for_sale | float | Y | 可供出售金融资产 |
| htm_invest | float | Y | 持有至到期投资 |
| lt_eqt_invest | float | Y | 长期股权投资 |
| invest_real_estate | float | Y | 投资性房地产 |
| time_deposits | float | Y | 定期存款 |
| oth_assets | float | Y | 其他资产 |
| lt_rec | float | Y | 长期应收款 |
| fix_assets | float | Y | 固定资产 |
| cip | float | Y | 在建工程 |
| const_materials | float | Y | 工程物资 |
| fixed_assets_disp | float | Y | 固定资产清理 |
| produc_bio_assets | float | Y | 生产性生物资产 |
| oil_and_gas_assets | float | Y | 油气资产 |
| intan_assets | float | Y | 无形资产 |
| r_and_d | float | Y | 研发支出 |
| goodwill | float | Y | 商誉 |
| lt_amor_exp | float | Y | 长期待摊费用 |
| defer_tax_assets | float | Y | 递延所得税资产 |
| decr_in_disbur | float | Y | 发放贷款及垫款 |
| oth_nca | float | Y | 其他非流动资产 |
| total_nca | float | Y | 非流动资产合计 |
| cash_reser_cb | float | Y | 现金及存放中央银行款项 |
| depos_in_oth_bfi | float | Y | 存放同业和其它金融机构款项 |
| prec_metals | float | Y | 贵金属 |
| deriv_assets | float | Y | 衍生金融资产 |
| rr_reins_une_prem | float | Y | 应收分保未到期责任准备金 |
| rr_reins_outstd_cla | float | Y | 应收分保未决赔款准备金 |
| rr_reins_lins_liab | float | Y | 应收分保寿险责任准备金 |
| rr_reins_lthins_liab | float | Y | 应收分保长期健康险责任准备金 |
| refund_depos | float | Y | 存出保证金 |
| ph_pledge_loans | float | Y | 保户质押贷款 |
| refund_cap_depos | float | Y | 存出资本保证金 |
| indep_acct_assets | float | Y | 独立账户资产 |
| client_depos | float | Y | 其中：客户资金存款 |
| client_prov | float | Y | 其中：客户备付金 |
| transac_seat_fee | float | Y | 其中:交易席位费 |
| invest_as_receiv | float | Y | 应收款项类投资 |
| total_assets | float | Y | 资产总计 |
| lt_borr | float | Y | 长期借款 |
| st_borr | float | Y | 短期借款 |
| cb_borr | float | Y | 向中央银行借款 |
| depos_ib_deposits | float | Y | 吸收存款及同业存放 |
| loan_oth_bank | float | Y | 拆入资金 |
| trading_fl | float | Y | 交易性金融负债 |
| notes_payable | float | Y | 应付票据 |
| acct_payable | float | Y | 应付账款 |
| adv_receipts | float | Y | 预收款项 |
| sold_for_repur_fa | float | Y | 卖出回购金融资产款 |
| comm_payable | float | Y | 应付手续费及佣金 |
| payroll_payable | float | Y | 应付职工薪酬 |
| taxes_payable | float | Y | 应交税费 |
| int_payable | float | Y | 应付利息 |
| div_payable | float | Y | 应付股利 |
| oth_payable | float | Y | 其他应付款 |
| acc_exp | float | Y | 预提费用 |
| deferred_inc | float | Y | 递延收益 |
| st_bonds_payable | float | Y | 应付短期债券 |
| payable_to_reinsurer | float | Y | 应付分保账款 |
| rsrv_insur_cont | float | Y | 保险合同准备金 |
| acting_trading_sec | float | Y | 代理买卖证券款 |
| acting_uw_sec | float | Y | 代理承销证券款 |
| non_cur_liab_due_1y | float | Y | 一年内到期的非流动负债 |
| oth_cur_liab | float | Y | 其他流动负债 |
| total_cur_liab | float | Y | 流动负债合计 |
| bond_payable | float | Y | 应付债券 |
| lt_payable | float | Y | 长期应付款 |
| specific_payables | float | Y | 专项应付款 |
| estimated_liab | float | Y | 预计负债 |
| defer_tax_liab | float | Y | 递延所得税负债 |
| defer_inc_non_cur_liab | float | Y | 递延收益-非流动负债 |
| oth_ncl | float | Y | 其他非流动负债 |
| total_ncl | float | Y | 非流动负债合计 |
| depos_oth_bfi | float | Y | 同业和其它金融机构存放款项 |
| deriv_liab | float | Y | 衍生金融负债 |
| depos | float | Y | 吸收存款 |
| agency_bus_liab | float | Y | 代理业务负债 |
| oth_liab | float | Y | 其他负债 |
| prem_receiv_adva | float | Y | 预收保费 |
| depos_received | float | Y | 存入保证金 |
| ph_invest | float | Y | 保户储金及投资款 |
| reser_une_prem | float | Y | 未到期责任准备金 |
| reser_outstd_claims | float | Y | 未决赔款准备金 |
| reser_lins_liab | float | Y | 寿险责任准备金 |
| reser_lthins_liab | float | Y | 长期健康险责任准备金 |
| indept_acc_liab | float | Y | 独立账户负债 |
| pledge_borr | float | Y | 质押借款 |
| indem_payable | float | Y | 应付赔付款 |
| policy_div_payable | float | Y | 应付保单红利 |
| total_liab | float | Y | 负债合计 |
| treasury_share | float | Y | 库存股 |
| ordin_risk_reser | float | Y | 一般风险准备 |
| forex_differ | float | Y | 外币报表折算差额 |
| invest_loss_unconf | float | Y | 未确认的投资损失 |
| minority_int | float | Y | 少数股东权益 |
| total_hldr_eqy_exc_min_int | float | Y | 股东权益合计(不含少数股东权益) |
| total_hldr_eqy_inc_min_int | float | Y | 股东权益合计(含少数股东权益) |
| total_liab_hldr_eqy | float | Y | 负债及股东权益总计 |
| lt_payroll_payable | float | Y | 长期应付职工薪酬 |
| oth_comp_income | float | Y | 其他综合收益 |
| lt_equity_invest | float | Y | 长期应收款 |
| total_eqt | float | Y | 所有者权益合计 |
| acc_receivable | float | N | 应收账款 |
| accounts_pay | float | N | 应付账款 |
| accounts_receiv_bill | float | N | 应收票据 |
| cip_total | float | N | 在建工程合计 |
| contract_assets | float | N | 合同资产 |
| contract_liab | float | N | 合同负债 |
| cost_fin_assets | float | N | 以摊余成本计量的金融资产 |
| debt_invest | float | N | 债权投资 |
| fair_value_fin_assets | float | N | 以公允价值计量且其变动计入当期损益的金融资产 |
| fix_assets_total | float | N | 固定资产合计 |
| hfs_assets | float | N | 持有待售资产 |
| hfs_sales | float | N | 持有待售负债 |
| lending_funds | float | N | 融出资金 |
| long_pay_total | float | N | 长期应付款合计 |
| oth_debt_invest | float | N | 其他债权投资 |
| oth_eqt_tools | float | N | 其他权益工具 |
| oth_eqt_tools_p_shr | float | N | 其他权益工具(优先股) |
| oth_eq_ppbond | float | N | 其他权益工具:永续债 |
| oth_pay_total | float | N | 其他应付款合计 |
| oth_rcv_total | float | N | 其他应收款合计 |
| payables | float | N | 应付款项 |
| st_fin_payable | float | N | 短期应付债券 |
| update_flag | string | Y | 更新标识 |

## 2. 利润表 (income)

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
|------|------|------|------|
| ts_code | str | Y | 股票代码 |
| ann_date | str | N | 公告日期（YYYYMMDD格式） |
| f_ann_date | str | N | 实际公告日期 |
| start_date | str | N | 公告日开始日期 |
| end_date | str | N | 公告日结束日期 |
| period | str | N | 报告期(每个季度最后一天的日期) |
| report_type | str | N | 报告类型 |
| comp_type | str | N | 公司类型（1一般工商业2银行3保险4证券） |

### 输出参数
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| ts_code | str | Y | TS代码 |
| ann_date | str | Y | 公告日期 |
| f_ann_date | str | Y | 实际公告日期 |
| end_date | str | Y | 报告期 |
| report_type | str | Y | 报告类型 |
| comp_type | str | Y | 公司类型(1一般工商业2银行3保险4证券) |
| end_type | str | Y | 报告期类型 |
| basic_eps | float | Y | 基本每股收益 |
| diluted_eps | float | Y | 稀释每股收益 |
| total_revenue | float | Y | 营业总收入 |
| revenue | float | Y | 营业收入 |
| int_income | float | Y | 利息收入 |
| prem_earned | float | Y | 已赚保费 |
| comm_income | float | Y | 手续费及佣金收入 |
| n_commis_income | float | Y | 手续费及佣金净收入 |
| n_oth_income | float | Y | 其他经营净收益 |
| n_oth_b_income | float | Y | 加:其他业务净收益 |
| prem_income | float | Y | 保险业务收入 |
| out_prem | float | Y | 减:分出保费 |
| une_prem_reser | float | Y | 提取未到期责任准备金 |
| reins_income | float | Y | 其中:分保费收入 |
| n_sec_tb_income | float | Y | 代理买卖证券业务净收入 |
| n_sec_uw_income | float | Y | 证券承销业务净收入 |
| n_asset_mg_income | float | Y | 受托客户资产管理业务净收入 |
| oth_b_income | float | Y | 其他业务收入 |
| fv_value_chg_gain | float | Y | 加:公允价值变动净收益 |
| invest_income | float | Y | 加:投资净收益 |
| ass_invest_income | float | Y | 其中:对联营企业和合营企业的投资收益 |
| forex_gain | float | Y | 加:汇兑净收益 |
| total_cogs | float | Y | 营业总成本 |
| oper_cost | float | Y | 减:营业成本 |
| int_exp | float | Y | 减:利息支出 |
| comm_exp | float | Y | 减:手续费及佣金支出 |
| biz_tax_surchg | float | Y | 减:营业税金及附加 |
| sell_exp | float | Y | 减:销售费用 |
| admin_exp | float | Y | 减:管理费用 |
| fin_exp | float | Y | 减:财务费用 |
| assets_impair_loss | float | Y | 减:资产减值损失 |
| prem_refund | float | Y | 退保金 |
| compens_payout | float | Y | 赔付总支出 |
| reser_insur_liab | float | Y | 提取保险责任准备金 |
| div_payt | float | Y | 保户红利支出 |
| reins_exp | float | Y | 分保费用 |
| oper_exp | float | Y | 营业支出 |
| compens_payout_refu | float | Y | 减:摊回赔付支出 |
| insur_reser_refu | float | Y | 减:摊回保险责任准备金 |
| reins_cost_refund | float | Y | 减:摊回分保费用 |
| other_bus_cost | float | Y | 其他业务成本 |
| operate_profit | float | Y | 营业利润 |
| non_oper_income | float | Y | 加:营业外收入 |
| non_oper_exp | float | Y | 减:营业外支出 |
| nca_disploss | float | Y | 其中:减:非流动资产处置净损失 |
| total_profit | float | Y | 利润总额 |
| income_tax | float | Y | 所得税费用 |
| n_income | float | Y | 净利润(含少数股东损益) |
| n_income_attr_p | float | Y | 净利润(不含少数股东损益) |
| minority_gain | float | Y | 少数股东损益 |
| oth_compr_income | float | Y | 其他综合收益 |
| t_compr_income | float | Y | 综合收益总额 |
| compr_inc_attr_p | float | Y | 归属于母公司(或股东)的综合收益总额 |
| compr_inc_attr_m_s | float | Y | 归属于少数股东的综合收益总额 |
| ebit | float | Y | 息税前利润 |
| ebitda | float | Y | 息税折旧摊销前利润 |
| insurance_exp | float | Y | 保险业务支出 |
| undist_profit | float | Y | 年初未分配利润 |
| distable_profit | float | Y | 可分配利润 |
| rd_exp | float | Y | 研发费用 |
| fin_exp_int_exp | float | Y | 财务费用:利息费用 |
| fin_exp_int_inc | float | Y | 财务费用:利息收入 |
| transfer_surplus_rese | float | Y | 盈余公积转入 |
| transfer_housing_imprest | float | Y | 住房周转金转入 |
| transfer_oth | float | Y | 其他转入 |
| adj_lossgain | float | Y | 调整以前年度损益 |
| withdra_legal_surplus | float | Y | 提取法定盈余公积 |
| withdra_legal_pubfund | float | Y | 提取法定公益金 |
| withdra_biz_devfund | float | Y | 提取企业发展基金 |
| withdra_rese_fund | float | Y | 提取储备基金 |
| withdra_oth_ersu | float | Y | 提取任意盈余公积金 |
| workers_welfare | float | Y | 职工奖金福利 |
| distr_profit_shrhder | float | Y | 可供股东分配的利润 |
| prfshare_payable_dvd | float | Y | 应付优先股股利 |
| comshare_payable_dvd | float | Y | 应付普通股股利 |
| capit_comstock_div | float | Y | 转作股本的普通股股利 |
| net_after_nr_lp_correct | float | N | 扣除非经常性损益后的净利润（更正前） |
| credit_impa_loss | float | N | 信用减值损失 |
| net_expo_hedging_benefits | float | N | 净敞口套期收益 |
| oth_impair_loss_assets | float | N | 其他资产减值损失 |
| total_opcost | float | N | 营业总成本（新准则） |
| asset_disp_income | float | N | 资产处置收益 |
| oth_income | float | N | 其他收益 |
| update_flag | string | Y | 更新标识 |

## 3. 现金流量表 (cashflow)

### 输入参数
| 名称 | 类型 | 必选 | 描述 |
|------|------|------|------|
| ts_code | str | Y | 股票代码 |
| ann_date | str | N | 公告日期（YYYYMMDD格式） |
| f_ann_date | str | N | 实际公告日期 |
| start_date | str | N | 公告日开始日期 |
| end_date | str | N | 公告日结束日期 |
| period | str | N | 报告期(每个季度最后一天的日期) |
| report_type | str | N | 报告类型 |
| comp_type | str | N | 公司类型：1一般工商业 2银行 3保险 4证券 |
| is_calc | int | N | 是否计算报表 |

### 输出参数
| 名称 | 类型 | 默认显示 | 描述 |
|------|------|----------|------|
| ts_code | str | Y | TS股票代码 |
| ann_date | str | Y | 公告日期 |
| f_ann_date | str | Y | 实际公告日期 |
| end_date | str | Y | 报告期 |
| comp_type | str | Y | 公司类型(1一般工商业2银行3保险4证券) |
| report_type | str | Y | 报表类型 |
| end_type | str | Y | 报告期类型 |
| net_profit | float | Y | 净利润 |
| finan_exp | float | Y | 财务费用 |
| c_fr_sale_sg | float | Y | 销售商品、提供劳务收到的现金 |
| recp_tax_rends | float | Y | 收到的税费返还 |
| n_depos_incr_fi | float | Y | 客户存款和同业存放款项净增加额 |
| n_incr_loans_cb | float | Y | 向中央银行借款净增加额 |
| n_inc_borr_oth_fi | float | Y | 向其他金融机构拆入资金净增加额 |
| prem_fr_orig_contr | float | Y | 收到原保险合同保费取得的现金 |
| n_incr_insured_dep | float | Y | 保户储金净增加额 |
| n_reinsur_prem | float | Y | 收到再保业务现金净额 |
| n_incr_disp_tfa | float | Y | 处置交易性金融资产净增加额 |
| ifc_cash_incr | float | Y | 收取利息和手续费净增加额 |
| n_incr_disp_faas | float | Y | 处置可供出售金融资产净增加额 |
| n_incr_loans_oth_bank | float | Y | 拆入资金净增加额 |
| n_cap_incr_repur | float | Y | 回购业务资金净增加额 |
| c_fr_oth_operate_a | float | Y | 收到其他与经营活动有关的现金 |
| c_inf_fr_operate_a | float | Y | 经营活动现金流入小计 |
| c_paid_goods_s | float | Y | 购买商品、接受劳务支付的现金 |
| c_paid_to_for_empl | float | Y | 支付给职工以及为职工支付的现金 |
| c_paid_for_taxes | float | Y | 支付的各项税费 |
| n_incr_clt_loan_adv | float | Y | 客户贷款及垫款净增加额 |
| n_incr_dep_cbob | float | Y | 存放央行和同业款项净增加额 |
| c_pay_claims_orig_inco | float | Y | 支付原保险合同赔付款项的现金 |
| pay_handling_chrg | float | Y | 支付手续费的现金 |
| pay_comm_insur_plcy | float | Y | 支付保单红利的现金 |
| oth_cash_pay_oper_act | float | Y | 支付其他与经营活动有关的现金 |
| st_cash_out_act | float | Y | 经营活动现金流出小计 |
| n_cashflow_act | float | Y | 经营活动产生的现金流量净额 |
| oth_recp_ral_inv_act | float | Y | 收到其他与投资活动有关的现金 |
| c_disp_withdrwl_invest | float | Y | 收回投资收到的现金 |
| c_recp_return_invest | float | Y | 取得投资收益收到的现金 |
| n_recp_disp_fiolta | float | Y | 处置固定资产、无形资产和其他长期资产收回的现金净额 |
| n_recp_disp_sobu | float | Y | 处置子公司及其他营业单位收到的现金净额 |
| stot_inflows_inv_act | float | Y | 投资活动现金流入小计 |
| c_pay_acq_const_fiolta | float | Y | 购建固定资产、无形资产和其他长期资产支付的现金 |
| c_paid_invest | float | Y | 投资支付的现金 |
| n_disp_subs_oth_biz | float | Y | 取得子公司及其他营业单位支付的现金净额 |
| oth_pay_ral_inv_act | float | Y | 支付其他与投资活动有关的现金 |
| n_incr_pledge_loan | float | Y | 质押贷款净增加额 |
| stot_out_inv_act | float | Y | 投资活动现金流出小计 |
| n_cashflow_inv_act | float | Y | 投资活动产生的现金流量净额 |
| c_recp_borrow | float | Y | 取得借款收到的现金 |
| proc_issue_bonds | float | Y | 发行债券收到的现金 |
| oth_cash_recp_ral_fnc_act | float | Y | 收到其他与筹资活动有关的现金 |
| stot_cash_in_fnc_act | float | Y | 筹资活动现金流入小计 |
| free_cashflow | float | Y | 企业自由现金流量 |
| c_prepay_amt_borr | float | Y | 偿还债务支付的现金 |
| c_pay_dist_dpcp_int_exp | float | Y | 分配股利、利润或偿付利息支付的现金 |
| incl_dvd_profit_paid_sc_ms | float | Y | 其中:子公司支付给少数股东的股利、利润 |
| oth_cashpay_ral_fnc_act | float | Y | 支付其他与筹资活动有关的现金 |
| stot_cashout_fnc_act | float | Y | 筹资活动现金流出小计 |
| n_cash_flows_fnc_act | float | Y | 筹资活动产生的现金流量净额 |
| eff_fx_flu_cash | float | Y | 汇率变动对现金的影响 |
| n_incr_cash_cash_equ | float | Y | 现金及现金等价物净增加额 |
| c_cash_equ_beg_period | float | Y | 期初现金及现金等价物余额 |
| c_cash_equ_end_period | float | Y | 期末现金及现金等价物余额 |
| c_recp_cap_contrib | float | Y | 吸收投资收到的现金 |
| incl_cash_rec_saims | float | Y | 其中:子公司吸收少数股东投资收到的现金 |
| uncon_invest_loss | float | Y | 未确认投资损失 |
| prov_depr_assets | float | Y | 资产减值准备 |
| depr_fa_coga_dpba | float | Y | 固定资产折旧、油气资产折耗、生产性生物资产折旧 |
| amort_intang_assets | float | Y | 无形资产摊销 |
| lt_amort_deferred_exp | float | Y | 长期待摊费用摊销 |
| decr_deferred_exp | float | Y | 待摊费用减少 |
| incr_acc_exp | float | Y | 待摊费用增加 |
| loss_disp_fiolta | float | Y | 处置固定资产、无形资产和其他长期资产的损失 |
| loss_scr_fa | float | Y | 固定资产报废损失 |
| loss_fv_chg | float | Y | 公允价值变动损失 |
| invest_loss | float | Y | 投资损失 |
| decr_def_inc_tax_assets | float | Y | 递延所得税资产减少 |
| incr_def_inc_tax_liab | float | Y | 递延所得税负债增加 |
| decr_inventories | float | Y | 存货的减少 |
| decr_oper_payable | float | Y | 经营性应收项目的减少 |
| incr_oper_payable | float | Y | 经营性应付项目的增加 |
| others | float | Y | 其他 |
| im_net_cashflow_oper_act | float | Y | 经营活动产生的现金流量净额(间接法) |
| conv_debt_into_cap | float | Y | 债务转为资本 |
| conv_copbonds_due_within_1y | float | Y | 一年内到期的可转换公司债券 |
| fa_fnc_leases | float | Y | 融资租入固定资产 |
| im_n_incr_cash_equ | float | Y | 现金及现金等价物净增加额(间接法) |
| net_dism_capital_add | float | Y | 净减少资本 |
| net_cash_rece_sec | float | Y | 收到的证券净额 |
| credit_impa_loss | float | N | 信用减值损失 |
| oth_loss_asset | float | Y | 其他资产损失 |
| end_bal_cash | float | Y | 现金的期末余额 |
| beg_bal_cash | float | Y | 现金的期初余额 |
| end_bal_cash_equ | float | Y | 现金等价物的期末余额 |
| beg_bal_cash_equ | float | Y | 现金等价物的期初余额 |
| update_flag | string | Y | 更新标识 |

## 4. 数据库模型对应关系

本文档中的字段已全部添加到以下数据库模型中：

- `models.py` 中的 `Income` 类对应利润表
- `models.py` 中的 `Cashflow` 类对应现金流量表
- `models.py` 中的 `Balancesheet` 类对应资产负债表

所有字段名称与 Tushare API 保持一致，确保数据的完整性和准确性。

## 5. 字段映射修正说明 (2026-03-14)

### 修正的问题

在之前的版本中，现金流量表补充资料部分（第640-666行）的字段映射存在严重的错位问题，每个字段的中文描述都对应到了下一个或下下个字段。

### 修正的字段

**现金流量表补充资料部分：**

| 字段名 | 修正前（错误） | 修正后（正确） |
|--------|---------------|---------------|
| `decr_deferred_exp` | 处置固定资产、无形资产和其他长期资产的损失 | 待摊费用减少 |
| `incr_acc_exp` | 固定资产报废损失 | 待摊费用增加 |
| `im_net_cashflow_oper_act` | 一年内到期的可转换公司债券 | 经营活动产生的现金流量净额(间接法) |
| `conv_debt_into_cap` | 融资租入固定资产 | 债务转为资本 |
| `conv_copbonds_due_within_1y` | 现金的期末余额 | 一年内到期的可转换公司债券 |
| `fa_fnc_leases` | 现金的期初余额 | 融资租入固定资产 |
| `im_n_incr_cash_equ` | 现金等价物的期末余额 | 现金及现金等价物净增加额(间接法) |
| `net_dism_capital_add` | 现金等价物的期初余额 | 净减少资本 |
| `net_cash_rece_sec` | 信用减值损失 | 收到的证券净额 |
| `credit_impa_loss` | 使用权资产折旧 | 信用减值损失 |
| `end_bal_cash` | 现金及现金等价物余额 | 现金的期末余额 |

### 删除的字段

- `use_right_assets_dep`: 此字段在 Tushare API 中不存在，已从映射中删除

### 验证方法

所有字段映射已通过以下方式验证：
1. 直接调用 Tushare API 获取实际返回的字段
2. 对比英文字段名和中文字段名的对应关系
3. 确保 `field_mapping.py` 中的映射与 API 返回完全一致

### 影响范围

此修正影响：
- `field_mapping.py` 中的 `CASHFLOW_FIELDS` 映射
- 数据保存时的字段翻译
- 数据查询和分析时的字段识别
