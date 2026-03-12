"""
Tushare API 客户端
用于获取股票财务数据
"""

import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import tushare as ts
import yaml
from field_mapping import translate_columns


class TushareClient:
    """Tushare API 客户端"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化 Tushare 客户端
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 设置日志
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 初始化 Tushare API
        ts.set_token(self.config['tushare']['token'])
        self.pro = ts.pro_api()
        
        # API 请求配置
        self.request_interval = self.config['tushare']['api']['request_interval']
        self.page_size = self.config['tushare']['api']['page_size']
        self.max_retries = self.config['tushare']['api']['max_retries']
        self.retry_interval = self.config['tushare']['api']['retry_interval']
        
        # 缓存股票上市日期
        self._stock_list_date_cache = {}
        
        self.logger.info("Tushare 客户端初始化成功")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    def _setup_logging(self):
        """设置日志"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 创建日志目录
        log_file = log_config.get('file')
        if log_file:
            import os
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            logging.basicConfig(level=log_level, format=log_format, filename=log_file)
        else:
            logging.basicConfig(level=log_level, format=log_format)
    
    def _make_request(self, api_func, **params) -> Optional[pd.DataFrame]:
        """
        调用 API 接口（带重试机制）
        
        Args:
            api_func: Tushare API 函数
            **params: API 参数
            
        Returns:
            返回的 DataFrame 或 None
        """
        for attempt in range(self.max_retries):
            try:
                result = api_func(**params)
                time.sleep(self.request_interval)  # 控制请求频率
                return result
            except Exception as e:
                self.logger.warning(f"API 请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_interval)
                else:
                    self.logger.error(f"API 请求最终失败: {e}")
                    return None
    
    def _make_request_with_pagination(self, api_func, **params) -> Optional[pd.DataFrame]:
        """
        分页获取数据（用于大数据量接口）
        
        Args:
            api_func: Tushare API 函数
            **params: API 参数
            
        Returns:
            合并后的 DataFrame 或 None
        """
        all_data = []
        offset = 0
        
        while True:
            # 添加分页参数
            paginated_params = {**params, 'offset': offset, 'limit': self.page_size}
            
            df = self._make_request(api_func, **paginated_params)
            
            if df is None or len(df) == 0:
                break
            
            all_data.append(df)
            offset += len(df)
            
            # 如果返回的数据少于页大小，说明已经是最后一页
            if len(df) < self.page_size:
                break
            
            self.logger.info(f"已获取 {offset} 条数据...")
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            self.logger.info(f"分页获取完成，共 {len(result)} 条数据")
            return result
        return None
    
    def get_stock_list_date(self, ts_code: str) -> Optional[str]:
        """
        获取股票上市日期
        
        Args:
            ts_code: 股票代码
            
        Returns:
            上市日期 (YYYYMMDD) 或 None
        """
        # 检查缓存
        if ts_code in self._stock_list_date_cache:
            return self._stock_list_date_cache[ts_code]
        
        try:
            df = self._make_request(self.pro.stock_basic, ts_code=ts_code, fields='ts_code,list_date')
            if df is not None and len(df) > 0:
                list_date = df.iloc[0]['list_date']
                if pd.notna(list_date) and list_date != '':
                    self._stock_list_date_cache[ts_code] = str(list_date)
                    return str(list_date)
        except Exception as e:
            self.logger.warning(f"获取 {ts_code} 上市日期失败: {e}")
        
        return None
    
    def get_fina_indicator(self, ts_code: str, start_date: Optional[str] = None,
                          end_date: Optional[str] = None, translate: bool = False) -> Optional[pd.DataFrame]:
        """
        获取财务指标表数据（约180个字段）
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            translate: 是否翻译字段名为中文
            
        Returns:
            财务指标 DataFrame 或 None
        """
        # 构建所有字段（包括默认显示为 N 的字段）
        fields = (
            # 基础信息
            "ts_code,ann_date,end_date,"
            # 每股指标
            "eps,dt_eps,total_revenue_ps,revenue_ps,capital_rese_ps,surplus_rese_ps,"
            "undist_profit_ps,diluted2_eps,bps,ocfps,retainedps,cfps,ebit_ps,fcff_ps,fcfe_ps,"
            # 盈利能力
            "roe,roe_waa,roe_dt,roa,npta,roic,roe_yearly,roa2_yearly,roe_avg,roa_yearly,roa_dp,roic_yearly,"
            # 营运能力
            "ar_turn,inv_turn,ca_turn,fa_turn,assets_turn,invturn_days,arturn_days,turn_days,total_fa_trun,"
            # 偿债能力
            "current_ratio,quick_ratio,cash_ratio,debt_to_assets,assets_to_eqt,dp_assets_to_eqt,"
            "debt_to_eqt,eqt_to_debt,eqt_to_interestdebt,"
            # 利润率
            "netprofit_margin,grossprofit_margin,gross_margin,cogs_of_sales,expense_of_sales,"
            "profit_to_gr,profit_to_op,"
            # 成长能力
            "basic_eps_yoy,dt_eps_yoy,cfps_yoy,op_yoy,ebt_yoy,netprofit_yoy,dt_netprofit_yoy,"
            "ocf_yoy,roe_yoy,bps_yoy,assets_yoy,eqt_yoy,tr_yoy,or_yoy,equity_yoy,"
            # 单季度指标
            "q_roe,q_dt_roe,q_npta,q_sales_yoy,q_sales_qoq,q_op_yoy,q_op_qoq,"
            "q_profit_yoy,q_profit_qoq,q_netprofit_yoy,q_netprofit_qoq,"
            # 其他重要指标
            "ebit,ebitda,fcff,fcfe,working_capital,networking_capital,tangible_asset,"
            "rd_exp,profit_dedt,extra_item,update_flag"
        )
        
        params = {
            "ts_code": ts_code,
            "fields": fields
        }
        
        # 如果没有指定日期范围，使用分页获取全部数据
        if not start_date:
            df = self._make_request_with_pagination(self.pro.fina_indicator, **params)
        else:
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            df = self._make_request(self.pro.fina_indicator, **params)
        
        # 如果没有指定开始日期，需要用上市日期过滤掉上市前的无效数据
        if df is not None and not start_date:
            list_date = self.get_stock_list_date(ts_code)
            if list_date:
                original_count = len(df)
                df = df[df['end_date'] >= list_date]
                if len(df) < original_count:
                    self.logger.info(f"{ts_code}: 过滤掉 {original_count - len(df)} 条上市前数据，上市日期: {list_date}")
        
        if df is not None and len(df) > 0:
            self.logger.info(f"获取 {ts_code} 财务指标数据成功，共 {len(df)} 条记录")
            # 翻译字段名
            if translate:
                df = translate_columns(df, 'fina_indicator')
        
        return df
    
    def get_balancesheet(self, ts_code: str, start_date: Optional[str] = None,
                        end_date: Optional[str] = None, translate: bool = False) -> Optional[pd.DataFrame]:
        """
        获取资产负债表数据（约156个字段）
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            translate: 是否翻译字段名为中文
            
        Returns:
            资产负债表 DataFrame 或 None
        """
        # 构建所有字段（包括默认显示为 N 的字段）
        fields = (
            # 基础信息
            "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,end_type,"
            # 股东权益
            "total_share,cap_rese,undistr_porfit,surplus_rese,special_rese,"
            # 流动资产
            "money_cap,trad_asset,notes_receiv,accounts_receiv,receiv_financing,"
            "oth_receiv,prepayment,div_receiv,int_receiv,inventories,amor_exp,"
            "nca_within_1y,sett_rsrv,loanto_oth_bank_fi,premium_receiv,reinsur_receiv,"
            "reinsur_res_receiv,pur_resale_fa,oth_cur_assets,total_cur_assets,"
            # 非流动资产
            "fa_avail_for_sale,htm_invest,lt_eqt_invest,invest_real_estate,time_deposits,"
            "oth_assets,lt_rec,fix_assets,cip,const_materials,fixed_assets_disp,"
            "produc_bio_assets,oil_and_gas_assets,intan_assets,r_and_d,goodwill,"
            "lt_amor_exp,defer_tax_assets,decr_in_disbur,oth_nca,total_nca,"
            # 金融资产（特殊）
            "cash_reser_cb,depos_in_oth_bfi,prec_metals,deriv_assets,"
            "rr_reins_une_prem,rr_reins_outstd_cla,rr_reins_lins_liab,rr_reins_lthins_liab,"
            "refund_depos,ph_pledge_loans,refund_cap_depos,indep_acct_assets,"
            "client_depos,client_prov,transac_seat_fee,invest_as_receiv,"
            # 资产总计
            "total_assets,"
            # 流动负债
            "lt_borr,st_borr,cb_borr,depos_ib_deposits,loan_oth_bank,trading_fl,"
            "notes_payable,acct_payable,adv_receipts,sold_for_repur_fa,comm_payable,"
            "payroll_payable,taxes_payable,int_payable,div_payable,oth_payable,"
            "acc_exp,deferred_inc,st_bonds_payable,payable_to_reinsurer,"
            "rsrv_insur_cont,acting_trading_sec,acting_uw_sec,non_cur_liab_due_1y,"
            "oth_cur_liab,total_cur_liab,"
            # 非流动负债
            "bond_payable,lt_payable,specific_payables,estimated_liab,defer_tax_liab,"
            "defer_inc_non_cur_liab,oth_ncl,total_ncl,"
            # 金融负债（特殊）
            "depos_oth_bfi,deriv_liab,depos,agency_bus_liab,oth_liab,"
            "prem_receiv_adva,depos_received,ph_invest,reser_une_prem,"
            "reser_outstd_claims,reser_lins_liab,reser_lthins_liab,"
            "indept_acc_liab,pledge_borr,indem_payable,policy_div_payable,"
            # 负债合计
            "total_liab,"
            # 股东权益
            "treasury_share,ordin_risk_reser,forex_differ,invest_loss_unconf,"
            "minority_int,total_hldr_eqy_exc_min_int,total_hldr_eqy_inc_min_int,"
            "total_liab_hldr_eqy,lt_payroll_payable,oth_comp_income,lt_equity_invest,total_eqt,"
            # 隐藏字段（默认显示为 N）
            "acc_receivable,accounts_pay,accounts_receiv_bill,cip_total,"
            "contract_assets,contract_liab,cost_fin_assets,debt_invest,"
            "fair_value_fin_assets,fix_assets_total,hfs_assets,hfs_sales,"
            "lending_funds,long_pay_total,oth_debt_invest,oth_eqt_tools,"
            "oth_eqt_tools_p_shr,oth_eq_ppbond,oth_pay_total,oth_rcv_total,"
            "payables,st_fin_payable,update_flag"
        )
        
        params = {
            "ts_code": ts_code,
            "fields": fields
        }
        
        # 如果没有指定日期范围，使用分页获取全部数据
        if not start_date:
            df = self._make_request_with_pagination(self.pro.balancesheet, **params)
        else:
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            df = self._make_request(self.pro.balancesheet, **params)
        
        # 如果没有指定开始日期，需要用上市日期过滤掉上市前的无效数据
        if df is not None and not start_date:
            list_date = self.get_stock_list_date(ts_code)
            if list_date:
                original_count = len(df)
                df = df[df['end_date'] >= list_date]
                if len(df) < original_count:
                    self.logger.info(f"{ts_code}: 过滤掉 {original_count - len(df)} 条上市前数据，上市日期: {list_date}")
        
        if df is not None and len(df) > 0:
            self.logger.info(f"获取 {ts_code} 资产负债表数据成功，共 {len(df)} 条记录")
            # 翻译字段名
            if translate:
                df = translate_columns(df, 'balancesheet')
        
        return df
    
    def get_income(self, ts_code: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None, translate: bool = False) -> Optional[pd.DataFrame]:
        """
        获取利润表数据（约94个字段）
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            translate: 是否翻译字段名为中文
            
        Returns:
            利润表 DataFrame 或 None
        """
        # 构建所有字段（包括默认显示为 N 的字段）
        fields = (
            # 基础信息
            "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,end_type,"
            # 每股指标
            "basic_eps,diluted_eps,"
            # 营业收入
            "total_revenue,revenue,int_income,prem_earned,comm_income,"
            "n_commis_income,n_oth_income,n_oth_b_income,prem_income,"
            "out_prem,une_prem_reser,reins_income,n_sec_tb_income,"
            "n_sec_uw_income,n_asset_mg_income,oth_b_income,"
            # 其他收益
            "fv_value_chg_gain,invest_income,ass_invest_income,forex_gain,"
            # 营业成本
            "total_cogs,oper_cost,int_exp,comm_exp,biz_tax_surchg,"
            "sell_exp,admin_exp,fin_exp,assets_impair_loss,"
            # 保险业务成本
            "prem_refund,compens_payout,reser_insur_liab,div_payt,reins_exp,oper_exp,"
            "compens_payout_refu,insur_reser_refu,reins_cost_refund,other_bus_cost,"
            # 营业利润
            "operate_profit,"
            # 营业外收支
            "non_oper_income,non_oper_exp,nca_disploss,"
            # 利润总额
            "total_profit,income_tax,"
            # 净利润
            "n_income,n_income_attr_p,minority_gain,"
            # 综合收益
            "oth_compr_income,t_compr_income,compr_inc_attr_p,compr_inc_attr_m_s,"
            # 其他指标
            "ebit,ebitda,insurance_exp,undist_profit,distable_profit,"
            "rd_exp,fin_exp_int_exp,fin_exp_int_inc,"
            "transfer_surplus_rese,transfer_housing_imprest,transfer_oth,"
            "adj_lossgain,withdra_legal_surplus,withdra_legal_pubfund,"
            "withdra_biz_devfund,withdra_rese_fund,withdra_oth_ersu,"
            "workers_welfare,distr_profit_shrhder,prfshare_payable_dvd,"
            "comshare_payable_dvd,capit_comstock_div,"
            # 隐藏字段（默认显示为 N）
            "net_after_nr_lp_correct,credit_impa_loss,net_expo_hedging_benefits,"
            "oth_impair_loss_assets,total_opcost,asset_disp_income,oth_income,update_flag"
        )
        
        params = {
            "ts_code": ts_code,
            "fields": fields
        }
        
        # 如果没有指定日期范围，使用分页获取全部数据
        if not start_date:
            df = self._make_request_with_pagination(self.pro.income, **params)
        else:
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            df = self._make_request(self.pro.income, **params)
        
        # 如果没有指定开始日期，需要用上市日期过滤掉上市前的无效数据
        if df is not None and not start_date:
            list_date = self.get_stock_list_date(ts_code)
            if list_date:
                original_count = len(df)
                df = df[df['end_date'] >= list_date]
                if len(df) < original_count:
                    self.logger.info(f"{ts_code}: 过滤掉 {original_count - len(df)} 条上市前数据，上市日期: {list_date}")
        
        if df is not None and len(df) > 0:
            self.logger.info(f"获取 {ts_code} 利润表数据成功，共 {len(df)} 条记录")
            # 翻译字段名
            if translate:
                df = translate_columns(df, 'income')
        
        return df
    
    def get_cashflow(self, ts_code: str, start_date: Optional[str] = None,
                     end_date: Optional[str] = None, translate: bool = False) -> Optional[pd.DataFrame]:
        """
        获取现金流量表数据（约99个字段）
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            translate: 是否翻译字段名为中文
            
        Returns:
            现金流量表 DataFrame 或 None
        """
        # 构建所有字段（包括默认显示为 N 的字段）
        fields = (
            # 基础信息
            "ts_code,ann_date,f_ann_date,end_date,comp_type,report_type,end_type,"
            # 净利润调整
            "net_profit,finan_exp,"
            # 经营活动现金流 - 流入
            "c_fr_sale_sg,recp_tax_rends,n_depos_incr_fi,n_incr_loans_cb,"
            "n_inc_borr_oth_fi,prem_fr_orig_contr,n_incr_insured_dep,"
            "n_reinsur_prem,n_incr_disp_tfa,ifc_cash_incr,n_incr_disp_faas,"
            "n_incr_loans_oth_bank,n_cap_incr_repur,c_fr_oth_operate_a,"
            "c_inf_fr_operate_a,"
            # 经营活动现金流 - 流出
            "c_paid_goods_s,c_paid_to_for_empl,c_paid_for_taxes,"
            "n_incr_clt_loan_adv,n_incr_dep_cbob,c_pay_claims_orig_inco,"
            "pay_handling_chrg,pay_comm_insur_plcy,oth_cash_pay_oper_act,"
            "st_cash_out_act,"
            # 经营活动现金流净额
            "n_cashflow_act,"
            # 投资活动现金流 - 流入
            "oth_recp_ral_inv_act,c_disp_withdrwl_invest,c_recp_return_invest,"
            "n_recp_disp_fiolta,n_recp_disp_sobu,stot_inflows_inv_act,"
            # 投资活动现金流 - 流出
            "c_pay_acq_const_fiolta,c_paid_invest,n_disp_subs_oth_biz,"
            "oth_pay_ral_inv_act,n_incr_pledge_loan,stot_out_inv_act,"
            # 投资活动现金流净额
            "n_cashflow_inv_act,"
            # 筹资活动现金流 - 流入
            "c_recp_borrow,proc_issue_bonds,oth_cash_recp_ral_fnc_act,"
            "stot_cash_in_fnc_act,"
            # 筹资活动现金流 - 流出
            "free_cashflow,c_prepay_amt_borr,c_pay_dist_dpcp_int_exp,"
            "incl_dvd_profit_paid_sc_ms,oth_cashpay_ral_fnc_act,stot_cashout_fnc_act,"
            # 筹资活动现金流净额
            "n_cash_flows_fnc_act,"
            # 其他
            "eff_fx_flu_cash,n_incr_cash_cash_equ,c_cash_equ_beg_period,"
            "c_cash_equ_end_period,c_recp_cap_contrib,incl_cash_rec_saims,"
            "uncon_invest_loss,"
            # 补充资料
            "prov_depr_assets,depr_fa_coga_dpba,amort_intang_assets,"
            "lt_amort_deferred_exp,decr_deferred_exp,incr_acc_exp,"
            "loss_disp_fiolta,loss_scr_fa,loss_fv_chg,invest_loss,"
            "decr_def_inc_tax_assets,incr_def_inc_tax_liab,decr_inventories,"
            "decr_oper_payable,incr_oper_payable,others,"
            "im_net_cashflow_oper_act,conv_debt_into_cap,"
            "conv_copbonds_due_within_1y,fa_fnc_leases,im_n_incr_cash_equ,"
            "net_dism_capital_add,net_cash_rece_sec,"
            # 隐藏字段（默认显示为 N）
            "credit_impa_loss,use_right_assets_dep,oth_loss_asset,"
            "end_bal_cash,beg_bal_cash,end_bal_cash_equ,beg_bal_cash_equ,update_flag"
        )
        
        params = {
            "ts_code": ts_code,
            "fields": fields
        }
        
        # 如果没有指定日期范围，使用分页获取全部数据
        if not start_date:
            df = self._make_request_with_pagination(self.pro.cashflow, **params)
        else:
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            df = self._make_request(self.pro.cashflow, **params)
        
        # 如果没有指定开始日期，需要用上市日期过滤掉上市前的无效数据
        if df is not None and not start_date:
            list_date = self.get_stock_list_date(ts_code)
            if list_date:
                original_count = len(df)
                df = df[df['end_date'] >= list_date]
                if len(df) < original_count:
                    self.logger.info(f"{ts_code}: 过滤掉 {original_count - len(df)} 条上市前数据，上市日期: {list_date}")
        
        if df is not None and len(df) > 0:
            self.logger.info(f"获取 {ts_code} 现金流量表数据成功，共 {len(df)} 条记录")
            # 翻译字段名
            if translate:
                df = translate_columns(df, 'cashflow')
        
        return df
    
    def get_all_financial_data(self, ts_code: str, start_date: Optional[str] = None,
                               end_date: Optional[str] = None, translate: bool = False) -> Dict[str, Optional[pd.DataFrame]]:
        """
        获取某家公司的全部财务数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            translate: 是否翻译字段名为中文
            
        Returns:
            包含所有财务报表的字典
        """
        self.logger.info(f"开始获取 {ts_code} 的完整财务数据...")
        
        result = {
            'fina_indicator': self.get_fina_indicator(ts_code, start_date, end_date, translate),
            'balancesheet': self.get_balancesheet(ts_code, start_date, end_date, translate),
            'income': self.get_income(ts_code, start_date, end_date, translate),
            'cashflow': self.get_cashflow(ts_code, start_date, end_date, translate)
        }
        
        # 统计数据
        total_records = sum(len(df) for df in result.values() if df is not None)
        self.logger.info(f"获取完成！共 {total_records} 条记录")
        
        return result
    
    def save_to_csv(self, data: Dict[str, Optional[pd.DataFrame]], ts_code: str, output_dir: str = None):
        """
        将数据保存为 CSV 文件
        
        Args:
            data: 财务数据字典
            ts_code: 股票代码
            output_dir: 输出目录
        """
        if output_dir is None:
            output_dir = self.config['data']['output_dir']
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for name, df in data.items():
            if df is not None and len(df) > 0:
                filename = f"{output_dir}/{ts_code}_{name}.csv"
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                self.logger.info(f"已保存: {filename}")
    
    def save_to_excel(self, data: Dict[str, Optional[pd.DataFrame]], ts_code: str, output_dir: str = None):
        """
        将数据保存为 Excel 文件（每个报表一个 sheet）
        
        Args:
            data: 财务数据字典
            ts_code: 股票代码
            output_dir: 输出目录
        """
        if output_dir is None:
            output_dir = self.config['data']['output_dir']
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{output_dir}/{ts_code}_financial_data.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for name, df in data.items():
                if df is not None and len(df) > 0:
                    df.to_excel(writer, sheet_name=name, index=False)
        
        self.logger.info(f"已保存: {filename}")
