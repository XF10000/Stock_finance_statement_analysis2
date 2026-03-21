"""
核心指标分析报告生成器 - ECharts版本
支持时间轴同步缩放、默认显示最近10年、CSV导出
"""

import pandas as pd
import json
from datetime import datetime
import sqlite3
from financial_data_manager import FinancialDataManager
from core_indicators_analyzer import CoreIndicatorsAnalyzer
from financial_data_analyzer import FinancialDataAnalyzer


class FinalReportGenerator:
    """核心指标报告生成器（ECharts版本）"""
    
    def __init__(self, db_path: str = 'database/financial_data.db'):
        self.db = FinancialDataManager(db_path)
        self.analyzer = CoreIndicatorsAnalyzer()
        self.market_analyzer = FinancialDataAnalyzer(self.db)
        
        # 指标配置
        self.indicators_config = [
            {
                'key': 'indicator1',
                'title': '指标1：回款能力 - 应收账款周转率对数 vs 毛利率',
                'description': '衡量公司应收账款管理效率、回款能力与产品盈利能力的综合表现（周转率已取对数）',
                'calculation': """• 应收账款周转率 = TTM营业收入 / 平均应收账款<br>
            • 平均应收账款 = (当期应收账款 + 去年同期应收账款) / 2<br>
            • TTM营业收入 = 最近四个季度的单季度营业收入之和<br>
            • 报告中显示的是对数值：ln(应收账款周转率)""",
                'analysis': [
                    '<strong>10年数据透视：</strong>应收账款周转率在全A样本中呈对数正态分布，真实性具备保障',
                    '<strong>虚增收入检验逻辑：</strong>应收账款周转率=营业收入/应收账款，通常大于1，因此如果通过虚增应收账款来虚增营业收入，分子分母同时增加相同的值，应收账款周转率大概率下降。应收账款周转率下降意味着企业在产业链上的竞争力减弱',
                    '<strong>毛利率交叉验证：</strong>但是营业成本很难随营业收入等比例虚增（折旧源于历史成本，员工工资需要和社保数据对应），如果通过虚增应收账款来虚增营业收入，毛利率可能上升，这又意味着企业议价权提高，与应收账款周转率指向不一致',
                    '<strong>一致性检验：</strong>因此，检验应收账款周转率和毛利率走势一致性，是重要的报表质量验证方法，不一致不一定有问题，但是需要给出合理解释'
                ],
                'metrics': [
                    {'col': '应收账款周转率对数', 'pct_col': 'ar_turnover_log_percentile', 'name': '应收账款周转率对数', 'color': '#C41E3A', 'unit': 'ln(次)', 'db_col': 'ar_turnover_log'},
                    {'col': '毛利率', 'pct_col': 'gross_margin_percentile', 'name': '毛利率', 'color': '#F5A623', 'unit': '%', 'db_col': 'gross_margin'}
                ]
            },
            {
                'key': 'indicator2',
                'title': '指标2：再投资质量 - 长期资产周转率对数',
                'description': '评估公司长期资产的使用效率和再投资质量，识别跑冒滴漏风险',
                'calculation': """• 长期资产周转率 = TTM营业收入 / 平均长期经营资产<br>
            • 平均长期经营资产 = (当期长期经营资产 + 去年同期长期经营资产) / 2<br>
            • <strong>长期经营资产</strong> = 固定资产 + 在建工程 + 生产性生物资产 + 油气资产 + 使用权资产 + 无形资产 + 开发支出 + 商誉 + 长期待摊费用 + 其他非流动资产<br>
            • 若该公司配置了资产重分类规则，则在上述基准值基础上相应加/减特定科目<br>　　（例：美的集团将「其他非流动资产」归入金融资产，从长期经营资产中扣除）<br>
            • TTM营业收入 = 最近四个季度的单季度营业收入之和<br>
            • 报告中显示的是对数值：ln(长期资产周转率)""",
                'analysis': [
                    '<strong>10年数据透视：</strong>营业收入/(固定资产+无形资产)在全A样本中呈对数正态分布',
                    '<strong>影响因素：</strong>影响固定资产周转率的因素包括单位产能造价、产能利用率、产品单价，一方面反映再投资质量，同时可以反映跑冒滴漏程度',
                    '<strong>三步循环法检验：</strong>如果上市公司采用了完整的"三步循环法"一般会将虚增的利润(或者跑冒滴漏)变成了固定资产、无形资产等长期资产，再通过未来折旧或者减值消化，由于资产负债表是累积式的，周转率指标会发生趋势性下降',
                    '<strong>分析要点：</strong>无论是哪种情况，固定资产+无形资产周转率下降，尤其是单个公司在全A样本中的分位数下降，都代表存量资产以及再投资质量下降，是重大的负面指标；反之则意味着资产利用效率、产业竞争力实打实改善'
                ],
                'metrics': [
                    {'col': '长期经营资产周转率对数', 'pct_col': 'lta_turnover_log_percentile', 'name': '长期资产周转率对数', 'color': '#C41E3A', 'unit': 'ln(次)', 'db_col': 'lta_turnover_log'}
                ]
            },
            {
                'key': 'indicator3',
                'title': '指标3：产业链地位 - 营运净资本比率',
                'description': '评估公司在产业链中的地位和议价能力，以及资金运用效率',
                'calculation': """• 营运净资本 = 应收账款 + 应收票据 + 应收款项融资 + 合同资产 - 应付账款 - 应付票据 - 合同负债<br>
            • 营运净资本比率 = 营运净资本 / 总资产 × 100%<br>
            • 负值表示公司占用上下游资金，正值表示被上下游占用资金""",
                'analysis': [
                    '<strong>10年数据透视：</strong>营运净资本占总资产的比例在全A样本呈正态分布，真实性具备保障',
                    '<strong>双重含义：</strong>营运净资本(应收账款+应收票据+应收款项融资+合同资产-应付账款-应付票据-合同负债)占比一方面体现上市公司资金运用效率，即不能创造收益的在途资金占比，另一方面反映公司在上下游产业链中的地位',
                    '<strong>分布特征：</strong>该指标是所有指标中，全A样本分布"最正态"的一个，且全A样本中位数非常接近零',
                    '<strong>龙头验证：</strong>尤其注意单个公司的该指标在全A样本中的分位数的边际变化。如果该公司在估值中的叙事是"龙头优势明显、强者恒强"，营运净资本占比在全A样本中的分位数就应该持续下降，或者绝对分位数很低，否则就是重大不一致，需要找到充足的理由解释'
                ],
                'metrics': [
                    {'col': '净营运资本比率', 'pct_col': 'working_capital_ratio_percentile', 'name': '营运净资本比率', 'color': '#C41E3A', 'unit': '%', 'db_col': 'working_capital_ratio'}
                ]
            },
            {
                'key': 'indicator4',
                'title': '指标4：真实盈利能力 - 经营现金流比率',
                'description': '评估公司真实的盈利能力和现金创造能力，数值越高说明盈利质量越好',
                'calculation': """• 经营现金流比率 = TTM经营活动现金流量净额 / 总资产 × 100%<br>
            • TTM经营活动现金流量净额 = 最近四个季度的单季度经营现金流之和<br>
            • 该比率反映企业通过经营活动创造现金的能力""",
                'analysis': [
                    '<strong>10年数据透视：</strong>经营性现金流量净额/总资产在全A样本呈正态分布，真实性具备保障',
                    '<strong>等价ROA：</strong>经营性现金流量净额中包含财务费用，因此分母用总资产，该指标相当于ROA。如之前所述，全A样本ROE存在调节的可能性，该指标更能体现资产的现金流创造能力',
                    '<strong>市场基准：</strong>2024年全A样本该指标的中位数只有4.3%，反映了A股市场加杠杆之前的"平均盈利水平"；而2025Q1分布则呈现明显的左侧厚尾(历年一季度都有这个特点)，中位数接近零，即大部分公司一季度回款一般，如果单个公司一季度回款较好，则尤为不易',
                    '<strong>叙事一致性：</strong>该指标的绝对值高低本身无谓多空，而是要对比财报中的画像与估值中隐含的叙事的一致性，包括历史趋势与全A样本分位数走势'
                ],
                'metrics': [
                    {'col': '经营现金流比率', 'pct_col': 'ocf_ratio_percentile', 'name': '经营现金流比率', 'color': '#C41E3A', 'unit': '%', 'db_col': 'ocf_ratio'}
                ]
            }
        ]
    
    def generate_report(self, ts_code: str, output_path: str = None):
        """生成完整报告"""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"data/{ts_code}_核心指标_{timestamp}.html"
        
        print(f"正在生成 {ts_code} 的分析报告...")
        
        # 获取股票基本信息
        stock_info = self._get_stock_info(ts_code)
        
        # 获取核心指标数据
        indicators = self._get_indicators(ts_code)
        
        if indicators is None or len(indicators) == 0:
            print(f"未找到 {ts_code} 的核心指标数据")
            return None
        
        # 筛选年度+TTM数据
        indicators = self._filter_annual_ttm_data(indicators)
        
        # 获取分位数历史数据
        percentile_history = self._get_percentile_history(ts_code)
        
        # 筛选年度+TTM数据的分位数
        if len(percentile_history) > 0:
            percentile_history = self._filter_annual_ttm_data(percentile_history.rename(columns={'end_date': '报告期'}))
            percentile_history = percentile_history.rename(columns={'报告期': 'end_date'})
        
        # 获取市场中位数历史数据
        market_medians = self._get_market_medians()
        
        # 导出CSV文件
        self._export_to_csv(ts_code, indicators, percentile_history, market_medians, output_path)
        
        # 生成HTML
        html = self._generate_full_html(ts_code, stock_info, indicators, percentile_history, market_medians)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✓ 报告已生成: {output_path}")
        return output_path
    
    def _get_stock_info(self, ts_code: str):
        """获取股票基本信息"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        row = cursor.execute(
            "SELECT ts_code, name, market, list_date FROM stock_list WHERE ts_code = ?",
            (ts_code,)
        ).fetchone()
        
        conn.close()
        
        if row is None:
            return {'ts_code': ts_code, 'name': '未知', 'market': '未知', 'list_date': '未知'}
        
        return {
            'ts_code': row[0],
            'name': row[1],
            'market': row[2],
            'list_date': row[3]
        }
    
    def _get_indicators(self, ts_code: str) -> pd.DataFrame:
        """获取核心指标数据"""
        conn = self.db.get_connection()
        query = '''
            SELECT end_date, ar_turnover_log, gross_margin, lta_turnover_log,
                   working_capital_ratio, ocf_ratio
            FROM core_indicators
            WHERE ts_code = ?
            ORDER BY end_date
        '''
        df = pd.read_sql_query(query, conn, params=(ts_code,))
        
        # 重命名列
        df = df.rename(columns={
            'end_date': '报告期',
            'ar_turnover_log': '应收账款周转率对数',
            'gross_margin': '毛利率',
            'lta_turnover_log': '长期经营资产周转率对数',
            'working_capital_ratio': '净营运资本比率',
            'ocf_ratio': '经营现金流比率'
        })
        
        return df
    
    def _get_percentile_history(self, ts_code: str) -> pd.DataFrame:
        """获取分位数历史数据"""
        conn = self.db.get_connection()
        query = '''
            SELECT end_date, ar_turnover_log_percentile, gross_margin_percentile,
                   lta_turnover_log_percentile, working_capital_ratio_percentile,
                   ocf_ratio_percentile
            FROM core_indicators
            WHERE ts_code = ?
            ORDER BY end_date
        '''
        return pd.read_sql_query(query, conn, params=(ts_code,))
    
    def _get_market_medians(self) -> pd.DataFrame:
        """获取市场中位数历史数据"""
        conn = self.db.get_connection()
        query = '''
            SELECT end_date, indicator_name, median
            FROM market_distribution
            ORDER BY end_date, indicator_name
        '''
        df = pd.read_sql_query(query, conn)
        
        # 确保 end_date 是整数类型
        df['end_date'] = df['end_date'].astype(int)
        
        # 转换为宽格式
        df_pivot = df.pivot(index='end_date', columns='indicator_name', values='median').reset_index()
        
        # 重命名列以匹配代码中的使用
        column_mapping = {
            'ar_turnover_log': 'ar_turnover_log_p50',
            'gross_margin': 'gross_margin_p50',
            'lta_turnover_log': 'lta_turnover_log_p50',
            'working_capital_ratio': 'working_capital_ratio_p50',
            'ocf_ratio': 'ocf_ratio_p50'
        }
        
        df_pivot = df_pivot.rename(columns=column_mapping)
        
        return df_pivot
    
    def _filter_annual_ttm_data(self, df):
        """筛选年度数据 + 最新年份的最新季度TTM数据"""
        if '报告期' not in df.columns or len(df) == 0:
            return df
        
        df = df.copy()
        df['报告期_str'] = df['报告期'].astype(str)
        
        # 1. 保留所有年度数据（12月31日）
        annual_data = df[df['报告期_str'].str.endswith('1231')].copy()
        
        # 2. 找出最新年份
        latest_year = df['报告期_str'].str[:4].max()
        
        # 3. 检查最新年份是否有年报
        has_annual = any(df['报告期_str'].str.startswith(latest_year) & 
                         df['报告期_str'].str.endswith('1231'))
        
        # 4. 如果最新年份没有年报，添加该年份的最新季度
        if not has_annual:
            latest_year_data = df[df['报告期_str'].str.startswith(latest_year)]
            if len(latest_year_data) > 0:
                latest_quarter = latest_year_data.sort_values('报告期', ascending=False).iloc[0:1]
                result = pd.concat([annual_data, latest_quarter])
            else:
                result = annual_data
        else:
            result = annual_data
        
        return result.drop(columns=['报告期_str']).sort_values('报告期')
    
    def _format_period(self, period):
        """格式化报告期显示"""
        # 处理各种数据类型
        if isinstance(period, str):
            period = float(period) if '.' in period else int(period)
        if isinstance(period, float):
            period = int(period)
        period_str = str(period)
        year = period_str[:4]
        month = period_str[4:6]
        
        if month == '12':
            return f"{year}年"
        elif month == '03':
            return f"{year}Q1-TTM"
        elif month == '06':
            return f"{year}Q2-TTM"
        elif month == '09':
            return f"{year}Q3-TTM"
        else:
            return f"{year}年"
    
    def _export_to_csv(self, ts_code, indicators, percentile_history, market_medians, html_path):
        """导出核心指标数据到CSV（转置格式，时间横向显示）"""
        # 合并指标数据和分位数数据
        if len(percentile_history) > 0:
            # 重命名分位数列
            pct_rename = {
                'end_date': '报告期',
                'ar_turnover_log_percentile': '应收账款周转率对数_分位数',
                'gross_margin_percentile': '毛利率_分位数',
                'lta_turnover_log_percentile': '长期资产周转率对数_分位数',
                'working_capital_ratio_percentile': '营运净资本比率_分位数',
                'ocf_ratio_percentile': '经营现金流比率_分位数'
            }
            pct_df = percentile_history.rename(columns=pct_rename)
            
            # 合并
            export_df = pd.merge(indicators, pct_df, on='报告期', how='left')
        else:
            export_df = indicators.copy()
        
        # 添加市场中位数数据
        for _, row in export_df.iterrows():
            period_int = int(row['报告期'])
            market_row = market_medians[market_medians['end_date'] == period_int]
            if len(market_row) > 0:
                export_df.loc[export_df['报告期'] == row['报告期'], '应收账款周转率对数_全A中位数'] = market_row.iloc[0].get('ar_turnover_log_p50', None)
                export_df.loc[export_df['报告期'] == row['报告期'], '毛利率_全A中位数'] = market_row.iloc[0].get('gross_margin_p50', None)
                export_df.loc[export_df['报告期'] == row['报告期'], '长期资产周转率对数_全A中位数'] = market_row.iloc[0].get('lta_turnover_log_p50', None)
                export_df.loc[export_df['报告期'] == row['报告期'], '营运净资本比率_全A中位数'] = market_row.iloc[0].get('working_capital_ratio_p50', None)
                export_df.loc[export_df['报告期'] == row['报告期'], '经营现金流比率_全A中位数'] = market_row.iloc[0].get('ocf_ratio_p50', None)
        
        # 格式化报告期作为列名
        period_labels = [self._format_period(p) for p in export_df['报告期']]
        
        # 转置：将报告期作为列，指标作为行
        # 选择要导出的指标列
        indicator_cols = [
            '应收账款周转率对数', '应收账款周转率对数_分位数', '应收账款周转率对数_全A中位数',
            '毛利率', '毛利率_分位数', '毛利率_全A中位数',
            '长期经营资产周转率对数', '长期资产周转率对数_分位数', '长期资产周转率对数_全A中位数',
            '净营运资本比率', '营运净资本比率_分位数', '营运净资本比率_全A中位数',
            '经营现金流比率', '经营现金流比率_分位数', '经营现金流比率_全A中位数'
        ]
        
        # 创建转置后的DataFrame
        transposed_data = {'指标': []}
        for label in period_labels:
            transposed_data[label] = []
        
        # 填充数据
        for col in indicator_cols:
            if col in export_df.columns:
                transposed_data['指标'].append(col)
                for i, label in enumerate(period_labels):
                    value = export_df.iloc[i][col]
                    transposed_data[label].append(value)
        
        transposed_df = pd.DataFrame(transposed_data)
        
        # 保存CSV
        csv_path = html_path.replace('.html', '.csv')
        transposed_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ 核心指标数据已导出到: {csv_path}")
    
    def _generate_full_html(self, ts_code, stock_info, indicators, percentile_history, market_medians):
        """生成完整HTML（使用ECharts）"""
        
        # 准备所有图表
        all_charts = []
        chart_counter = 0
        
        for config in self.indicators_config:
            if len(config['metrics']) == 2:
                # 指标1：双指标
                chart_counter += 1
                all_charts.append({
                    'id': chart_counter,
                    'type': 'dual_company',
                    'config': config,
                    'ts_code': ts_code,
                    'indicators': indicators,
                    'market_medians': market_medians
                })
                
                chart_counter += 1
                all_charts.append({
                    'id': chart_counter,
                    'type': 'dual_market',
                    'config': config,
                    'ts_code': ts_code,
                    'indicators': indicators,
                    'market_medians': market_medians
                })
            else:
                # 其他指标：单指标
                metric = config['metrics'][0]
                
                chart_counter += 1
                all_charts.append({
                    'id': chart_counter,
                    'type': 'single_vs_market',
                    'config': config,
                    'metric': metric,
                    'ts_code': ts_code,
                    'indicators': indicators,
                    'market_medians': market_medians
                })
                
                chart_counter += 1
                all_charts.append({
                    'id': chart_counter,
                    'type': 'percentile',
                    'config': config,
                    'metric': metric,
                    'ts_code': ts_code,
                    'percentile_history': percentile_history
                })
        
        # 生成图表脚本
        chart_scripts = []
        chart_ids = []
        
        for chart in all_charts:
            script = self._generate_chart_script(chart)
            chart_scripts.append(script)
            chart_ids.append(f"chart_{chart['id']}")
        
        # 生成章节HTML
        sections_html = ''.join([self._generate_section_html(config, all_charts) for config in self.indicators_config])
        
        # 生成完整HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ts_code} 财务指标分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{
            font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 40px;
            border-left: 4px solid #4CAF50;
            padding-left: 10px;
        }}
        .info-box {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .info-item {{
            display: inline-block;
            margin-right: 30px;
            margin-bottom: 10px;
        }}
        .info-label {{
            font-weight: bold;
            color: #666;
        }}
        .chart-container {{
            width: 100%;
            height: 500px;
            margin: 30px 0;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #999;
            font-size: 14px;
        }}
        details {{
            background-color: #f8f9fa;
            border-left: 4px solid #4CAF50;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        summary {{
            cursor: pointer;
            font-weight: bold;
            color: #4CAF50;
            padding: 5px 0;
            user-select: none;
        }}
        summary:hover {{
            color: #45a049;
        }}
        summary::marker {{
            color: #4CAF50;
        }}
        .analysis-content {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            line-height: 1.8;
        }}
        .analysis-content ol {{
            padding-left: 20px;
        }}
        .analysis-content li {{
            margin-bottom: 12px;
            color: #444;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{ts_code} 财务指标分析报告</h1>
        
        <div class="info-box">
            <div class="info-item">
                <span class="info-label">股票代码：</span>{ts_code}
            </div>
            <div class="info-item">
                <span class="info-label">股票名称：</span>{stock_info['name']}
            </div>
            <div class="info-item">
                <span class="info-label">分析日期：</span>{datetime.now().strftime('%Y-%m-%d')}
            </div>
            <div class="info-item">
                <span class="info-label">数据年限：</span>{len(indicators)}期
            </div>
        </div>

{sections_html}

        <div class="footer">
            <p>本报告由财务分析系统自动生成 | 数据来源: Tushare | 市场对比: 全A股样本</p>
        </div>
    </div>
    
    <script>
        // 图表初始化
        {chr(10).join(chart_scripts)}
        
        // 时间轴同步缩放 - 使用ECharts的connect功能
        var allCharts = [{', '.join(chart_ids)}];
        
        // 使用ECharts的group功能实现图表联动
        echarts.connect('coreIndicatorsGroup');
        allCharts.forEach(function(chart) {{
            chart.group = 'coreIndicatorsGroup';
        }});
        
        // 响应式调整
        window.addEventListener('resize', function() {{
            allCharts.forEach(function(chart) {{
                chart.resize();
            }});
        }});
    </script>
</body>
</html>'''
        
        return html
    
    def _generate_chart_script(self, chart_data):
        """生成ECharts图表脚本"""
        chart_id = chart_data['id']
        chart_type = chart_data['type']
        
        if chart_type == 'dual_company':
            return self._generate_dual_company_script(chart_data)
        elif chart_type == 'dual_market':
            return self._generate_dual_market_script(chart_data)
        elif chart_type == 'single_vs_market':
            return self._generate_single_vs_market_script(chart_data)
        elif chart_type == 'percentile':
            return self._generate_percentile_script(chart_data)
    
    def _generate_dual_company_script(self, chart_data):
        """生成双指标公司图表脚本"""
        chart_id = chart_data['id']
        config = chart_data['config']
        indicators = chart_data['indicators']
        ts_code = chart_data['ts_code']
        
        metric1 = config['metrics'][0]
        metric2 = config['metrics'][1]
        
        periods = [self._format_period(p) for p in indicators['报告期']]
        values1 = indicators[metric1['col']].tolist()
        values2 = indicators[metric2['col']].tolist()
        
        # 计算dataZoom的start值，默认显示最近10年
        total_dates = len(periods)
        zoom_start = ((total_dates - 10) / total_dates) * 100 if total_dates > 10 else 0
        
        series = [
            {
                'name': metric1['name'],
                'type': 'line',
                'data': values1,
                'yAxisIndex': 0,
                'lineStyle': {'width': 3, 'color': metric1['color']},
                'itemStyle': {'color': metric1['color']},
                'symbol': 'circle',
                'symbolSize': 6
            },
            {
                'name': metric2['name'],
                'type': 'line',
                'data': values2,
                'yAxisIndex': 1,
                'lineStyle': {'width': 3, 'color': metric2['color']},
                'itemStyle': {'color': metric2['color']},
                'symbol': 'circle',
                'symbolSize': 6
            }
        ]
        
        script = f'''
        var chart_{chart_id};
        (function() {{
            chart_{chart_id} = echarts.init(document.getElementById('chart_{chart_id}'));
            var option = {{
                title: {{
                    text: '{ts_code} - {metric1["name"]} vs {metric2["name"]}',
                    left: 'center',
                    textStyle: {{
                        fontSize: 18,
                        fontWeight: 'normal'
                    }}
                }},
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{
                        type: 'cross'
                    }}
                }},
                legend: {{
                    data: ['{metric1["name"]}', '{metric2["name"]}'],
                    bottom: 60,
                    left: 'center'
                }},
                grid: {{
                    left: '3%',
                    right: '8%',
                    bottom: '22%',
                    top: '15%',
                    containLabel: true
                }},
                dataZoom: [
                    {{
                        type: 'slider',
                        show: true,
                        xAxisIndex: [0],
                        start: {zoom_start:.2f},
                        end: 100,
                        bottom: 0
                    }},
                    {{
                        type: 'inside',
                        xAxisIndex: [0],
                        start: {zoom_start:.2f},
                        end: 100
                    }}
                ],
                xAxis: {{
                    type: 'category',
                    data: {json.dumps(periods, ensure_ascii=False)},
                    axisLabel: {{
                        rotate: 45,
                        fontSize: 11
                    }}
                }},
                yAxis: [
                    {{
                        type: 'value',
                        name: '{metric1["name"]}{metric1["unit"]}',
                        position: 'left',
                        scale: true
                    }},
                    {{
                        type: 'value',
                        name: '{metric2["name"]}{metric2["unit"]}',
                        position: 'right',
                        scale: true
                    }}
                ],
                series: {json.dumps(series, ensure_ascii=False)}
            }};
            chart_{chart_id}.setOption(option);
        }})();
        '''
        
        return script
    
    def _generate_dual_market_script(self, chart_data):
        """生成双指标市场中位数图表脚本"""
        chart_id = chart_data['id']
        config = chart_data['config']
        indicators = chart_data['indicators']
        market_medians = chart_data['market_medians']
        
        metric1 = config['metrics'][0]
        metric2 = config['metrics'][1]
        
        # 匹配市场中位数数据
        periods = []
        values1 = []
        values2 = []
        
        for period in indicators['报告期']:
            period_int = int(period)
            market_row = market_medians[market_medians['end_date'] == period_int]
            if len(market_row) > 0:
                periods.append(self._format_period(period))
                values1.append(market_row.iloc[0]['ar_turnover_log_p50'])
                values2.append(market_row.iloc[0]['gross_margin_p50'])
        
        # 计算dataZoom的start值
        total_dates = len(periods)
        zoom_start = ((total_dates - 10) / total_dates) * 100 if total_dates > 10 else 0
        
        series = [
            {
                'name': metric1['name'],
                'type': 'line',
                'data': values1,
                'yAxisIndex': 0,
                'lineStyle': {'width': 3, 'color': metric1['color'], 'type': 'dashed'},
                'itemStyle': {'color': metric1['color']},
                'symbol': 'circle',
                'symbolSize': 6
            },
            {
                'name': metric2['name'],
                'type': 'line',
                'data': values2,
                'yAxisIndex': 1,
                'lineStyle': {'width': 3, 'color': metric2['color'], 'type': 'dashed'},
                'itemStyle': {'color': metric2['color']},
                'symbol': 'circle',
                'symbolSize': 6
            }
        ]
        
        script = f'''
        var chart_{chart_id};
        (function() {{
            chart_{chart_id} = echarts.init(document.getElementById('chart_{chart_id}'));
            var option = {{
                title: {{
                    text: '全A股中位数 - {metric1["name"]} vs {metric2["name"]}',
                    left: 'center',
                    textStyle: {{
                        fontSize: 18,
                        fontWeight: 'normal'
                    }}
                }},
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{
                        type: 'cross'
                    }}
                }},
                legend: {{
                    data: ['{metric1["name"]}', '{metric2["name"]}'],
                    bottom: 60,
                    left: 'center'
                }},
                grid: {{
                    left: '3%',
                    right: '8%',
                    bottom: '22%',
                    top: '15%',
                    containLabel: true
                }},
                dataZoom: [
                    {{
                        type: 'slider',
                        show: true,
                        xAxisIndex: [0],
                        start: {zoom_start:.2f},
                        end: 100,
                        bottom: 0
                    }},
                    {{
                        type: 'inside',
                        xAxisIndex: [0],
                        start: {zoom_start:.2f},
                        end: 100
                    }}
                ],
                xAxis: {{
                    type: 'category',
                    data: {json.dumps(periods, ensure_ascii=False)},
                    axisLabel: {{
                        rotate: 45,
                        fontSize: 11
                    }}
                }},
                yAxis: [
                    {{
                        type: 'value',
                        name: '{metric1["name"]}{metric1["unit"]}',
                        position: 'left',
                        scale: true
                    }},
                    {{
                        type: 'value',
                        name: '{metric2["name"]}{metric2["unit"]}',
                        position: 'right',
                        scale: true
                    }}
                ],
                series: {json.dumps(series, ensure_ascii=False)}
            }};
            chart_{chart_id}.setOption(option);
        }})();
        '''
        
        return script
    
    def _generate_single_vs_market_script(self, chart_data):
        """生成单指标公司vs市场图表脚本"""
        chart_id = chart_data['id']
        metric = chart_data['metric']
        indicators = chart_data['indicators']
        market_medians = chart_data['market_medians']
        ts_code = chart_data['ts_code']
        
        periods = [self._format_period(p) for p in indicators['报告期']]
        company_values = indicators[metric['col']].tolist()
        
        # 匹配市场中位数数据
        market_values = []
        for period in indicators['报告期']:
            period_int = int(period)
            market_row = market_medians[market_medians['end_date'] == period_int]
            if len(market_row) > 0:
                col_name = metric['db_col'] + '_p50'
                market_values.append(market_row.iloc[0][col_name])
            else:
                market_values.append(None)
        
        # 计算dataZoom的start值
        total_dates = len(periods)
        zoom_start = ((total_dates - 10) / total_dates) * 100 if total_dates > 10 else 0
        
        series = [
            {
                'name': ts_code,
                'type': 'line',
                'data': company_values,
                'lineStyle': {'width': 3, 'color': metric['color']},
                'itemStyle': {'color': metric['color']},
                'symbol': 'circle',
                'symbolSize': 6
            },
            {
                'name': '全A股中位数',
                'type': 'line',
                'data': market_values,
                'lineStyle': {'width': 3, 'color': '#F5A623', 'type': 'dashed'},
                'itemStyle': {'color': '#F5A623'},
                'symbol': 'circle',
                'symbolSize': 6
            }
        ]
        
        script = f'''
        var chart_{chart_id};
        (function() {{
            chart_{chart_id} = echarts.init(document.getElementById('chart_{chart_id}'));
            var option = {{
                title: {{
                    text: '{ts_code} vs 全A股中位数 - {metric["name"]}历史走势对比',
                    left: 'center',
                    textStyle: {{
                        fontSize: 18,
                        fontWeight: 'normal'
                    }}
                }},
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{
                        type: 'cross'
                    }}
                }},
                legend: {{
                    data: ['{ts_code}', '全A股中位数'],
                    bottom: 60,
                    left: 'center'
                }},
                grid: {{
                    left: '3%',
                    right: '4%',
                    bottom: '22%',
                    top: '15%',
                    containLabel: true
                }},
                dataZoom: [
                    {{
                        type: 'slider',
                        show: true,
                        xAxisIndex: [0],
                        start: {zoom_start:.2f},
                        end: 100,
                        bottom: 0
                    }},
                    {{
                        type: 'inside',
                        xAxisIndex: [0],
                        start: {zoom_start:.2f},
                        end: 100
                    }}
                ],
                xAxis: {{
                    type: 'category',
                    data: {json.dumps(periods, ensure_ascii=False)},
                    axisLabel: {{
                        rotate: 45,
                        fontSize: 11
                    }}
                }},
                yAxis: {{
                    type: 'value',
                    name: '{metric["name"]}{metric["unit"]}'
                }},
                series: {json.dumps(series, ensure_ascii=False)}
            }};
            chart_{chart_id}.setOption(option);
        }})();
        '''
        
        return script
    
    def _generate_percentile_script(self, chart_data):
        """生成分位数排名图表脚本"""
        chart_id = chart_data['id']
        metric = chart_data['metric']
        percentile_history = chart_data['percentile_history']
        ts_code = chart_data['ts_code']
        
        if len(percentile_history) == 0:
            return f"var chart_{chart_id} = null; // No data"
        
        periods = [self._format_period(p) for p in percentile_history['end_date']]
        percentiles = percentile_history[metric['pct_col']].tolist()
        
        # 计算dataZoom的start值
        total_dates = len(periods)
        zoom_start = ((total_dates - 10) / total_dates) * 100 if total_dates > 10 else 0
        
        series = [
            {
                'name': '分位数排名',
                'type': 'line',
                'data': percentiles,
                'lineStyle': {'width': 3, 'color': '#4CAF50'},
                'itemStyle': {'color': '#4CAF50'},
                'symbol': 'circle',
                'symbolSize': 6,
                'areaStyle': {'color': 'rgba(76, 175, 80, 0.1)'}
            }
        ]
        
        script = f'''
        var chart_{chart_id};
        (function() {{
            chart_{chart_id} = echarts.init(document.getElementById('chart_{chart_id}'));
            var option = {{
                title: {{
                    text: '{ts_code} - {metric["name"]}全A股分位数排名历史',
                    left: 'center',
                    textStyle: {{
                        fontSize: 18,
                        fontWeight: 'normal'
                    }}
                }},
                tooltip: {{
                    trigger: 'axis',
                    formatter: function(params) {{
                        return params[0].axisValue + '<br/>' +
                               params[0].marker + ' 分位数: ' + params[0].value.toFixed(1) + '%';
                    }}
                }},
                legend: {{
                    data: ['分位数排名'],
                    bottom: 60,
                    left: 'center'
                }},
                grid: {{
                    left: '3%',
                    right: '4%',
                    bottom: '22%',
                    top: '15%',
                    containLabel: true
                }},
                dataZoom: [
                    {{
                        type: 'slider',
                        show: true,
                        xAxisIndex: [0],
                        start: {zoom_start:.2f},
                        end: 100,
                        bottom: 0
                    }},
                    {{
                        type: 'inside',
                        xAxisIndex: [0],
                        start: {zoom_start:.2f},
                        end: 100
                    }}
                ],
                xAxis: {{
                    type: 'category',
                    data: {json.dumps(periods, ensure_ascii=False)},
                    axisLabel: {{
                        rotate: 45,
                        fontSize: 11
                    }}
                }},
                yAxis: {{
                    type: 'value',
                    name: '分位数排名 (%)',
                    min: 0,
                    max: 100
                }},
                series: {json.dumps(series, ensure_ascii=False)}
            }};
            
            // 添加参考线
            option.series.push({{
                name: '75%线',
                type: 'line',
                markLine: {{
                    silent: true,
                    lineStyle: {{
                        color: 'green',
                        type: 'dashed'
                    }},
                    data: [{{yAxis: 75, label: {{formatter: '75%', position: 'end'}}}}]
                }}
            }});
            option.series.push({{
                name: '50%线',
                type: 'line',
                markLine: {{
                    silent: true,
                    lineStyle: {{
                        color: 'gray',
                        type: 'dashed'
                    }},
                    data: [{{yAxis: 50, label: {{formatter: '中位数', position: 'end'}}}}]
                }}
            }});
            option.series.push({{
                name: '25%线',
                type: 'line',
                markLine: {{
                    silent: true,
                    lineStyle: {{
                        color: 'red',
                        type: 'dashed'
                    }},
                    data: [{{yAxis: 25, label: {{formatter: '25%', position: 'end'}}}}]
                }}
            }});
            
            chart_{chart_id}.setOption(option);
        }})();
        '''
        
        return script
    
    def _generate_section_html(self, config, all_charts):
        """生成指标章节HTML"""
        # 找到该指标的所有图表
        section_charts = [c for c in all_charts if c['config']['key'] == config['key']]
        
        chart_divs = []
        for i, chart in enumerate(section_charts):
            if i == 0:
                if len(config['metrics']) == 2:
                    chart_divs.append(f'<h3>图1：{chart["ts_code"]} - {config["metrics"][0]["name"]} vs {config["metrics"][1]["name"]}</h3>')
                else:
                    chart_divs.append(f'<h3>图1：{chart["ts_code"]} vs 全A股中位数 - {config["metrics"][0]["name"]}历史走势对比</h3>')
            elif i == 1:
                if len(config['metrics']) == 2:
                    chart_divs.append(f'<h3>图2：全A股中位数 - {config["metrics"][0]["name"]} vs {config["metrics"][1]["name"]}</h3>')
                else:
                    chart_divs.append(f'<h3>图2：{chart["ts_code"]} - {config["metrics"][0]["name"]}全A股分位数排名历史</h3>')
            
            chart_divs.append(f'<div id="chart_{chart["id"]}" class="chart-container"></div>')
        
        chart_html = ''.join(chart_divs)
        
        analysis_items = ''.join([f'<li>{item}</li>' for item in config['analysis']])
        
        return f'''
<h2 style="color: #C41E3A; border-bottom: 2px solid #C41E3A; padding-bottom: 10px;">{config['title']}</h2>
<p style="color: #666; margin-bottom: 20px;">
    {config['description']}<br>
    <strong>计算方法：</strong><br>
    {config['calculation']}
</p>
<details>
    <summary>📊 点击展开：{config['title']}深度分析说明</summary>
    <div class="analysis-content">
        <ol>
            {analysis_items}
        </ol>
    </div>
</details>
{chart_html}
'''
