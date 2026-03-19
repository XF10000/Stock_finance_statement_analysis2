"""
HTML财务报告生成器
基于年报+TTM数据生成交互式HTML报告，包含多个财务指标图表
使用ECharts实现可缩放的时间轴图表
"""

import pandas as pd
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os


class HTMLReportGenerator:
    """HTML财务报告生成器"""
    
    # 配色方案（与样例图表一致）
    COLORS = {
        'blue': '#5B9BD5',      # 蓝色 - 营业收入、短期债务、固定资产
        'orange': '#ED7D31',    # 橙色 - 息税前经营利润、长期债务
        'gray': '#A5A5A5',      # 灰色 - 营业成本、所有者权益
        'green': '#70AD47',     # 绿色 - 毛利
        'yellow': '#FFC000',    # 黄色 - 净利润、有息债务率
        'red': '#FF0000',       # 红色 - 毛利率线
        'dark_gray': '#595959', # 深灰色 - 其他
        'light_blue': '#4472C4',# 浅蓝色
        'brown': '#C65911',     # 棕色
    }
    
    def __init__(self, company_name: str = "", stock_code: str = ""):
        """
        初始化报告生成器
        
        Args:
            company_name: 公司名称
            stock_code: 股票代码
        """
        self.company_name = company_name
        self.stock_code = stock_code
        
    def generate_report(
        self,
        balance_data: pd.DataFrame,
        income_data: pd.DataFrame,
        cashflow_data: pd.DataFrame,
        output_path: str = "financial_report.html"
    ) -> str:
        """
        生成完整的HTML财务报告
        
        Args:
            balance_data: 资产负债表年报+TTM数据
            income_data: 利润表年报+TTM数据
            cashflow_data: 现金流量表年报+TTM数据
            output_path: 输出文件路径
            
        Returns:
            生成的HTML文件路径
        """
        # 确保所有 DataFrame 的列名都是字符串类型（避免整数列名导致的匹配失败）
        balance_data = balance_data.copy()
        balance_data.columns = [str(col) for col in balance_data.columns]
        
        income_data = income_data.copy()
        income_data.columns = [str(col) for col in income_data.columns]
        
        cashflow_data = cashflow_data.copy()
        cashflow_data.columns = [str(col) for col in cashflow_data.columns]
        
        # 提取日期列（排除"项目"列），并反转顺序（从远到近）
        date_columns = [col for col in balance_data.columns if col != '项目']
        date_columns = list(reversed(date_columns))  # 反转时间轴：从远期到近期
        
        # 生成各个图表的配置
        charts_config = []
        
        # 1. 资产负债分析图表（放在前面）
        balance_charts = self._generate_balance_charts(balance_data, date_columns)
        
        # 为需要利润表数据的图表添加营业收入数据
        for chart in balance_charts:
            if chart.get('needs_income_data'):
                # 从利润表中提取营业收入数据
                revenue_data = self._extract_chart_data(income_data, date_columns, {
                    'bar': ['营业收入']
                })
                # 合并数据
                chart['data']['series'].update(revenue_data['series'])
                # 添加计算字段
                chart['calculated_fields'] = {
                    '经营资本-营业收入比例': ('周转性经营投入合计', '营业收入'),
                    '存货-营业收入比例': ('存货', '营业收入')
                }
        
        charts_config.extend(balance_charts)
        
        # 2. 利润分析图表
        profit_charts = self._generate_profit_charts(income_data, date_columns)
        
        # 为营业费用图表添加特殊计算字段
        for chart in profit_charts:
            if chart.get('needs_special_calc'):
                self._add_operating_expense_calculations(chart, income_data, date_columns)
        
        charts_config.extend(profit_charts)
        
        # 3. 经营效率分析图表
        efficiency_charts = self._generate_efficiency_charts(balance_data, income_data, date_columns)
        
        # 为图表添加计算字段
        for chart in efficiency_charts:
            if chart.get('needs_roic_only_calc'):
                self._add_roic_only_calculations(chart, balance_data, income_data, date_columns)
            elif chart.get('needs_roe_roic_calc'):
                self._add_roe_roic_calculations(chart, balance_data, income_data, date_columns)
            elif chart.get('needs_asset_efficiency_calc'):
                self._add_asset_efficiency_calculations(chart, balance_data, income_data, date_columns)
            elif chart.get('needs_turnover_days_calc'):
                self._add_turnover_days_calculations(chart, balance_data, income_data, date_columns)
            elif chart.get('needs_turnover_ratio_calc'):
                self._add_turnover_ratio_calculations(chart, balance_data, income_data, date_columns)
        
        charts_config.extend(efficiency_charts)
        
        # 4. 财务成本分析图表
        finance_cost_charts = self._generate_finance_cost_charts(income_data, date_columns)
        
        # 为图表添加计算字段
        for chart in finance_cost_charts:
            if chart.get('needs_finance_cost_calc'):
                self._add_finance_cost_calculations(chart, income_data, date_columns)
        
        charts_config.extend(finance_cost_charts)
        
        # 5. 长期资产投资和并购活动分析图表
        capex_charts = self._generate_capex_charts(balance_data, cashflow_data, date_columns)
        
        # 为图表添加计算字段
        for chart in capex_charts:
            if chart.get('needs_capex_calc'):
                self._add_capex_calculations(chart, balance_data, cashflow_data, date_columns)
        
        charts_config.extend(capex_charts)
        
        # 6. 投资收益分析图表
        investment_income_charts = self._generate_investment_income_charts(balance_data, income_data, date_columns)
        
        # 为图表添加计算字段
        for chart in investment_income_charts:
            if chart.get('needs_investment_income_calc'):
                self._add_investment_income_calculations(chart, balance_data, income_data, date_columns)
        
        charts_config.extend(investment_income_charts)
        
        # 7. 自由现金流分析图表（FCFF和FCFE）
        fcf_charts = self._generate_fcf_charts(balance_data, income_data, cashflow_data, date_columns)
        charts_config.extend(fcf_charts)
        
        # 生成HTML内容
        html_content = self._generate_html_template(charts_config, date_columns)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ HTML报告已生成: {output_path}")
        return output_path
    
    def _generate_profit_charts(self, df: pd.DataFrame, date_columns: List[str]) -> List[Dict]:
        """生成利润分析图表配置"""
        charts = []
        
        # 图表1: 营收、成本、毛利、净利趋势
        chart1 = {
            'id': 'chart_revenue_profit',
            'title': '毛利、净利、营收、成本趋势',
            'type': 'bar_line',
            'data': self._extract_chart_data(df, date_columns, {
                'bar': ['营业收入', '营业成本', '毛利', '净利润'],
                'line': ['毛利率', '净利润率']
            }),
            'colors': {
                '营业收入': self.COLORS['blue'],
                '营业成本': self.COLORS['gray'],
                '毛利': self.COLORS['green'],
                '净利润': self.COLORS['yellow'],
                '毛利率': self.COLORS['red'],
                '净利润率': self.COLORS['orange']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent'
        }
        charts.append(chart1)
        
        # 图表2: 息税前经营收入利润EBIT、利润率
        chart2 = {
            'id': 'chart_ebit',
            'title': '息税前经营收入利润EBIT、利润率',
            'type': 'bar_line',
            'data': self._extract_chart_data(df, date_columns, {
                'bar': ['营业收入', '息税前经营利润'],
                'line': ['息税前经营利润率']
            }),
            'colors': {
                '营业收入': self.COLORS['blue'],
                '息税前经营利润': self.COLORS['orange'],
                '息税前经营利润率': self.COLORS['gray']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent',
            'calculated_fields': {
                '息税前经营利润率': ('息税前经营利润', '营业收入')
            }
        }
        charts.append(chart2)
        
        # 图表3: 营业费用
        chart3 = {
            'id': 'chart_operating_expenses',
            'title': '营业费用',
            'type': 'bar_line',
            'data': self._extract_chart_data(df, date_columns, {
                'bar': ['销售费用', '管理费用', '研发费用', '税金及附加', 
                       '资产减值损失', '信用减值损失', '营业外收入', '营业外支出'],
                'line': ['销售费用率', '管理费用率', '研发费用率', '税金及附加率',
                        '经营资产减值损失率', '营业外收支净额率', '总费用率']
            }),
            'colors': {
                '销售费用': self.COLORS['orange'],
                '管理费用': self.COLORS['yellow'],
                '研发费用': self.COLORS['green'],
                '税金及附加': self.COLORS['gray'],
                '资产减值损失': self.COLORS['light_blue'],
                '信用减值损失': self.COLORS['brown'],
                '营业外收入': self.COLORS['blue'],
                '营业外支出': self.COLORS['dark_gray'],
                '销售费用率': self.COLORS['orange'],
                '管理费用率': self.COLORS['yellow'],
                '研发费用率': self.COLORS['green'],
                '税金及附加率': self.COLORS['gray'],
                '经营资产减值损失率': self.COLORS['blue'],
                '营业外收支净额率': self.COLORS['light_blue'],
                '总费用率': '#7030A0'  # 紫色
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent',
            'needs_special_calc': True  # 标记需要特殊计算
        }
        charts.append(chart3)
        
        return charts
    
    def _generate_balance_charts(self, df: pd.DataFrame, date_columns: List[str]) -> List[Dict]:
        """生成资产负债分析图表配置"""
        charts = []
        
        # 图表1: 资产变化及类别组成比例
        chart1 = {
            'id': 'chart_assets_composition',
            'title': '资产变化及类别组成比例',
            'type': 'stacked_bar',
            'data': self._extract_chart_data(df, date_columns, {
                'bar': ['金融资产合计', '长期股权投资', '周转性经营投入合计', '长期经营资产合计']
            }),
            'colors': {
                '金融资产合计': self.COLORS['blue'],
                '长期股权投资': self.COLORS['gray'],
                '周转性经营投入合计': self.COLORS['orange'],
                '长期经营资产合计': self.COLORS['yellow']
            },
            'y_axis_names': ['亿元', ''],
            'show_values': True
        }
        charts.append(chart1)
        
        # 图表2: 资本期限分析
        chart2 = {
            'id': 'chart_capital_structure',
            'title': '资本期限分析',
            'type': 'stacked_bar_line',
            'data': self._extract_chart_data(df, date_columns, {
                'bar': ['短期债务', '长期债务', '所有者权益合计'],
                'line': ['有息债务率']
            }),
            'colors': {
                '短期债务': self.COLORS['blue'],
                '长期债务': self.COLORS['orange'],
                '所有者权益合计': self.COLORS['gray'],
                '有息债务率': self.COLORS['yellow']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent',
            'show_values': True,
            'calculated_fields': {
                '有息债务率': ('有息债务合计', '资本总额')
            }
        }
        charts.append(chart2)
        
        # 图表3: 长期经营资产变化
        # 智能选择固定资产字段：优先使用"固定资产合计"，如果没有则使用"固定资产"
        # 检查"项目"列中是否包含该字段
        has_fixed_asset_total = '固定资产合计' in df['项目'].values if '项目' in df.columns else False
        fixed_asset_field = '固定资产合计' if has_fixed_asset_total else '固定资产'
        
        chart3 = {
            'id': 'chart_long_term_assets',
            'title': '长期经营资产变化',
            'type': 'stacked_bar',
            'data': self._extract_chart_data(df, date_columns, {
                'bar': [fixed_asset_field, '在建工程合计', '工程物资', '固定资产清理', 
                       '生产性生物资产', '公益性生物资产', '油气资产', '使用权资产',
                       '无形资产', '开发支出', '商誉', '长期待摊费用', 
                       '其他非流动资产', '递延所得税资产', '递延所得税负债(减项)']
            }),
            'colors': {
                '固定资产': '#E6E6FA',
                '固定资产合计': '#E6E6FA',
                '在建工程合计': '#D8BFD8',
                '工程物资': '#C1A7DC',
                '固定资产清理': '#9370DB',
                '生产性生物资产': '#8A2BE2',
                '公益性生物资产': '#FFA07A',
                '油气资产': '#FF7F50',
                '使用权资产': '#FFDAB9',
                '无形资产': '#FF8C00',
                '开发支出': '#0077BE',
                '商誉': '#008ECC',
                '长期待摊费用': '#00A6D6',
                '其他非流动资产': '#4BC0D9',
                '递延所得税资产': '#7ED5EA',
                '递延所得税负债(减项)': '#ADD8E6'
            },
            'y_axis_names': ['亿元', ''],
            'show_values': False
        }
        charts.append(chart3)
        
        # 图表4: 经营资本-营业收入比例
        chart4 = {
            'id': 'chart_working_capital_ratio',
            'title': '经营资本-营业收入比例',
            'type': 'bar_line',
            'data': self._extract_chart_data(df, date_columns, {
                'bar': ['周转性经营投入合计', '存货'],
                'line': []  # 计算字段会在后面添加
            }),
            'colors': {
                '周转性经营投入合计': self.COLORS['orange'],
                '存货': self.COLORS['yellow'],
                '经营资本-营业收入比例': self.COLORS['gray'],
                '存货-营业收入比例': self.COLORS['yellow']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent',
            'show_values': False,
            'needs_income_data': True  # 标记需要利润表数据
        }
        charts.append(chart4)
        
        return charts
    
    def _generate_cashflow_charts(self, df: pd.DataFrame, date_columns: List[str]) -> List[Dict]:
        """生成现金流分析图表配置"""
        charts = []
        
        # 图表1: 自由现金流分析
        chart1 = {
            'id': 'chart_free_cashflow',
            'title': '自由现金流分析',
            'type': 'bar_line',
            'data': self._extract_chart_data(df, date_columns, {
                'bar': ['经营现金流净额', '资本支出', '自由现金流'],
                'line': ['自由现金流/营业收入']
            }),
            'colors': {
                '经营现金流净额': self.COLORS['blue'],
                '资本支出': self.COLORS['orange'],
                '自由现金流': self.COLORS['green'],
                '自由现金流/营业收入': self.COLORS['red']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent'
        }
        charts.append(chart1)
        
        return charts
    
    def _generate_efficiency_charts(self, balance_df: pd.DataFrame, income_df: pd.DataFrame, date_columns: List[str]) -> List[Dict]:
        """生成经营效率分析图表配置"""
        charts = []
        
        # 图表1: ROIC（独立图表）
        chart1 = {
            'id': 'chart_roic',
            'title': 'ROIC',
            'type': 'bar_line',
            'data': self._extract_chart_data(balance_df, date_columns, {
                'bar': ['所有者权益合计', '有息债务合计', '金融资产合计'],
                'line': []
            }),
            'colors': {
                'Invested Capital': self.COLORS['blue'],
                '息前税后经营利润': self.COLORS['orange'],
                'ROIC': self.COLORS['gray'],
                '息前税后经营利润增速': self.COLORS['yellow']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent',
            'needs_roic_only_calc': True  # 标记需要ROIC计算（包含增速）
        }
        charts.append(chart1)
        
        # 图表2: Equity, Debt, ROE and ROIC（合并ROIC和ROE）
        chart2 = {
            'id': 'chart_roe_roic',
            'title': 'Equity, Debt, ROE and ROIC',
            'type': 'bar_line',
            'data': self._extract_chart_data(balance_df, date_columns, {
                'bar': ['有息债务合计', '所有者权益合计'],
                'line': []
            }),
            'colors': {
                '有息债务合计': self.COLORS['blue'],
                '所有者权益合计': self.COLORS['orange'],
                'ROIC': self.COLORS['gray'],
                'ROE': self.COLORS['yellow']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent',
            'needs_roe_roic_calc': True  # 标记需要ROE和ROIC计算
        }
        charts.append(chart2)
        
        # 图表3: 经营资产效率
        chart3 = {
            'id': 'chart_asset_efficiency',
            'title': '经营资产效率',
            'type': 'bar_line',
            'data': self._extract_chart_data(income_df, date_columns, {
                'bar': ['净利润'],
                'line': []
            }),
            'colors': {
                '净利润': self.COLORS['yellow'],
                '经营资产周转率': self.COLORS['blue'],
                '长期经营资产周转率': self.COLORS['orange'],
                '固定资产周转率': self.COLORS['gray']
            },
            'y_axis_names': ['亿元', '次'],
            'line_format': 'number',
            'needs_asset_efficiency_calc': True
        }
        charts.append(chart3)
        
        # 图表4: 周转天数及营业周期
        chart4 = {
            'id': 'chart_turnover_days',
            'title': '周转天数及营业周期',
            'type': 'line',
            'data': {'dates': date_columns, 'series': {}},
            'colors': {
                '应收账款周转天数': self.COLORS['blue'],
                '存货周转天数': self.COLORS['orange'],
                '应付账款周转天数': self.COLORS['gray'],
                '营业周期': self.COLORS['yellow'],
                '现金周期': '#4169E1'  # 深蓝色
            },
            'y_axis_names': ['天', ''],
            'line_format': 'number',
            'needs_turnover_days_calc': True
        }
        charts.append(chart4)
        
        # 图表5: 经营周转率
        chart5 = {
            'id': 'chart_turnover_ratio',
            'title': '经营周转率',
            'type': 'line',
            'data': {'dates': date_columns, 'series': {}},
            'colors': {
                '应收账款周转率': self.COLORS['blue'],
                '存货周转率': self.COLORS['orange'],
                '应付账款周转率': self.COLORS['gray'],
                '经营资产周转率': self.COLORS['yellow']
            },
            'y_axis_names': ['次', ''],
            'line_format': 'number',
            'needs_turnover_ratio_calc': True
        }
        charts.append(chart5)
        
        return charts
    
    def _add_operating_expense_calculations(self, chart: Dict, df: pd.DataFrame, date_columns: List[str]):
        """
        为营业费用图表添加特殊计算字段
        
        Args:
            chart: 图表配置字典
            df: 利润表数据DataFrame
            date_columns: 日期列列表
        """
        data = chart['data']
        series = data['series']
        
        # 提取需要的数据
        营业收入 = series.get('营业收入', {}).get('data', [])
        税金及附加 = series.get('税金及附加', {}).get('data', [])
        资产减值损失 = series.get('资产减值损失', {}).get('data', [])
        信用减值损失 = series.get('信用减值损失', {}).get('data', [])
        营业外收入 = series.get('营业外收入', {}).get('data', [])
        营业外支出 = series.get('营业外支出', {}).get('data', [])
        销售费用率 = series.get('销售费用率', {}).get('data', [])
        管理费用率 = series.get('管理费用率', {}).get('data', [])
        研发费用率 = series.get('研发费用率', {}).get('data', [])
        
        # 计算新字段
        税金及附加率_data = []
        经营资产减值损失率_data = []
        营业外收支净额_data = []
        营业外收支净额率_data = []
        总费用率_data = []
        
        for i in range(len(date_columns)):
            # 1. 税金及附加率 = 税金及附加 / 营业收入
            if 税金及附加 and 营业收入 and i < len(税金及附加) and i < len(营业收入):
                if 税金及附加[i] is not None and 营业收入[i] is not None and 营业收入[i] != 0:
                    税金及附加率_data.append((税金及附加[i] / 营业收入[i]) * 100)
                else:
                    税金及附加率_data.append(None)
            else:
                税金及附加率_data.append(None)
            
            # 2. 经营资产减值损失率 = (资产减值损失 + 信用减值损失) / 营业收入
            if 资产减值损失 and 信用减值损失 and 营业收入 and i < len(资产减值损失) and i < len(信用减值损失) and i < len(营业收入):
                asset_loss = 资产减值损失[i] if 资产减值损失[i] is not None else 0
                credit_loss = 信用减值损失[i] if 信用减值损失[i] is not None else 0
                if 营业收入[i] is not None and 营业收入[i] != 0:
                    经营资产减值损失率_data.append(((asset_loss + credit_loss) / 营业收入[i]) * 100)
                else:
                    经营资产减值损失率_data.append(None)
            else:
                经营资产减值损失率_data.append(None)
            
            # 3. 营业外收支净额 = 营业外收入 - 营业外支出
            if 营业外收入 and 营业外支出 and i < len(营业外收入) and i < len(营业外支出):
                income = 营业外收入[i] if 营业外收入[i] is not None else 0
                expense = 营业外支出[i] if 营业外支出[i] is not None else 0
                营业外收支净额_data.append(income - expense)
            else:
                营业外收支净额_data.append(None)
            
            # 4. 营业外收支净额率 = 营业外收支净额 / 营业收入
            if 营业外收支净额_data[i] is not None and 营业收入 and i < len(营业收入) and 营业收入[i] is not None and 营业收入[i] != 0:
                营业外收支净额率_data.append((营业外收支净额_data[i] / 营业收入[i]) * 100)
            else:
                营业外收支净额率_data.append(None)
            
            # 5. 总费用率 = 税金及附加率 + 销售费用率 + 管理费用率 + 经营资产减值损失率 + 营业外收支净额率
            total = 0
            count = 0
            if 税金及附加率_data[i] is not None:
                total += 税金及附加率_data[i]
                count += 1
            if 销售费用率 and i < len(销售费用率) and 销售费用率[i] is not None:
                total += 销售费用率[i]
                count += 1
            if 管理费用率 and i < len(管理费用率) and 管理费用率[i] is not None:
                total += 管理费用率[i]
                count += 1
            if 研发费用率 and i < len(研发费用率) and 研发费用率[i] is not None:
                total += 研发费用率[i]
                count += 1
            if 经营资产减值损失率_data[i] is not None:
                total += 经营资产减值损失率_data[i]
                count += 1
            if 营业外收支净额率_data[i] is not None:
                total += 营业外收支净额率_data[i]
                count += 1
            
            总费用率_data.append(total if count > 0 else None)
        
        # 添加计算字段到series
        series['税金及附加率'] = {'type': 'line', 'data': 税金及附加率_data}
        series['经营资产减值损失率'] = {'type': 'line', 'data': 经营资产减值损失率_data}
        series['营业外收支净额'] = {'type': 'bar', 'data': 营业外收支净额_data}
        series['营业外收支净额率'] = {'type': 'line', 'data': 营业外收支净额率_data}
        series['总费用率'] = {'type': 'line', 'data': 总费用率_data}
    
    def _add_roic_only_calculations(self, chart: Dict, balance_df: pd.DataFrame, income_df: pd.DataFrame, date_columns: List[str]):
        """
        为独立ROIC图表添加计算字段（包含息前税后经营利润增速）
        
        Args:
            chart: 图表配置字典
            balance_df: 资产负债表数据DataFrame
            income_df: 利润表数据DataFrame
            date_columns: 日期列列表
        """
        data = chart['data']
        series = data['series']
        
        # 从利润表提取息前税后经营利润
        income_data = self._extract_chart_data(income_df, date_columns, {
            'bar': ['息前税后经营利润']
        })
        series.update(income_data['series'])
        
        # 提取需要的数据
        所有者权益合计 = series.get('所有者权益合计', {}).get('data', [])
        有息债务合计 = series.get('有息债务合计', {}).get('data', [])
        金融资产合计 = series.get('金融资产合计', {}).get('data', [])
        息前税后经营利润 = series.get('息前税后经营利润', {}).get('data', [])
        
        # 计算 Invested Capital、ROIC 和息前税后经营利润增速
        invested_capital_data = []
        roic_data = []
        nopat_growth_data = []
        
        for i in range(len(date_columns)):
            equity = 所有者权益合计[i] if i < len(所有者权益合计) and 所有者权益合计[i] is not None else 0
            debt = 有息债务合计[i] if i < len(有息债务合计) and 有息债务合计[i] is not None else 0
            financial = 金融资产合计[i] if i < len(金融资产合计) and 金融资产合计[i] is not None else 0
            
            # Invested Capital = 所有者权益合计 + 有息债务合计 - 金融资产合计
            invested_capital = equity + debt - financial
            invested_capital_data.append(invested_capital if invested_capital != 0 else None)
            
            # ROIC = 息前税后经营利润 / 当期IC和前一期IC的均值
            if i > 0 and invested_capital_data[i] is not None and invested_capital_data[i-1] is not None:
                avg_ic = (invested_capital_data[i] + invested_capital_data[i-1]) / 2
                nopat = 息前税后经营利润[i] if i < len(息前税后经营利润) and 息前税后经营利润[i] is not None else 0
                if avg_ic != 0:
                    roic_data.append((nopat / avg_ic) * 100)
                else:
                    roic_data.append(None)
            else:
                roic_data.append(None)
            
            # 息前税后经营利润增速 = (当期NOPAT - 前期NOPAT) / 前期NOPAT
            if i > 0:
                current_nopat = 息前税后经营利润[i] if i < len(息前税后经营利润) and 息前税后经营利润[i] is not None else 0
                prev_nopat = 息前税后经营利润[i-1] if i-1 < len(息前税后经营利润) and 息前税后经营利润[i-1] is not None else 0
                
                if prev_nopat != 0:
                    nopat_growth_data.append(((current_nopat - prev_nopat) / prev_nopat) * 100)
                else:
                    nopat_growth_data.append(None)
            else:
                nopat_growth_data.append(None)
        
        # 添加计算字段到series
        series['Invested Capital'] = {'type': 'bar', 'data': invested_capital_data}
        series['ROIC'] = {'type': 'line', 'data': roic_data}
        series['息前税后经营利润增速'] = {'type': 'line', 'data': nopat_growth_data}
        
        # 移除原始字段，只保留计算后的字段
        series.pop('所有者权益合计', None)
        series.pop('有息债务合计', None)
        series.pop('金融资产合计', None)
    
    def _add_roe_roic_calculations(self, chart: Dict, balance_df: pd.DataFrame, income_df: pd.DataFrame, date_columns: List[str]):
        """
        为ROE和ROIC图表添加计算字段
        
        Args:
            chart: 图表配置字典
            balance_df: 资产负债表数据DataFrame
            income_df: 利润表数据DataFrame
            date_columns: 日期列列表
        """
        data = chart['data']
        series = data['series']
        
        # 从利润表提取息前税后经营利润和净利润
        income_data = self._extract_chart_data(income_df, date_columns, {
            'bar': ['息前税后经营利润', '净利润']
        })
        series.update(income_data['series'])
        
        # 从资产负债表提取金融资产合计（用于计算ROIC）
        balance_data = self._extract_chart_data(balance_df, date_columns, {
            'bar': ['金融资产合计']
        })
        series.update(balance_data['series'])
        
        # 提取需要的数据
        所有者权益合计 = series.get('所有者权益合计', {}).get('data', [])
        有息债务合计 = series.get('有息债务合计', {}).get('data', [])
        金融资产合计 = series.get('金融资产合计', {}).get('data', [])
        息前税后经营利润 = series.get('息前税后经营利润', {}).get('data', [])
        净利润 = series.get('净利润', {}).get('data', [])
        
        # 计算 ROIC 和 ROE
        roic_data = []
        roe_data = []
        
        for i in range(len(date_columns)):
            equity = 所有者权益合计[i] if i < len(所有者权益合计) and 所有者权益合计[i] is not None else 0
            debt = 有息债务合计[i] if i < len(有息债务合计) and 有息债务合计[i] is not None else 0
            financial = 金融资产合计[i] if i < len(金融资产合计) and 金融资产合计[i] is not None else 0
            
            # ROIC = 息前税后经营利润 / 当期IC和前一期IC的均值
            # Invested Capital = 所有者权益合计 + 有息债务合计 - 金融资产合计
            if i > 0:
                # 当期投入资本
                current_ic = equity + debt - financial
                # 前期投入资本
                prev_equity = 所有者权益合计[i-1] if i-1 < len(所有者权益合计) and 所有者权益合计[i-1] is not None else 0
                prev_debt = 有息债务合计[i-1] if i-1 < len(有息债务合计) and 有息债务合计[i-1] is not None else 0
                prev_financial = 金融资产合计[i-1] if i-1 < len(金融资产合计) and 金融资产合计[i-1] is not None else 0
                prev_ic = prev_equity + prev_debt - prev_financial
                
                # 平均投入资本
                avg_ic = (current_ic + prev_ic) / 2
                nopat = 息前税后经营利润[i] if i < len(息前税后经营利润) and 息前税后经营利润[i] is not None else 0
                
                if avg_ic != 0:
                    roic_data.append((nopat / avg_ic) * 100)
                else:
                    roic_data.append(None)
                
                # ROE = 净利润 / 当期所有者权益合计和前一期所有者权益合计的均值
                avg_equity = (equity + prev_equity) / 2
                net_profit = 净利润[i] if i < len(净利润) and 净利润[i] is not None else 0
                
                if avg_equity != 0:
                    roe_data.append((net_profit / avg_equity) * 100)
                else:
                    roe_data.append(None)
            else:
                roic_data.append(None)
                roe_data.append(None)
        
        # 添加计算字段到series
        series['ROIC'] = {'type': 'line', 'data': roic_data}
        series['ROE'] = {'type': 'line', 'data': roe_data}
        
        # 移除不需要在图表中显示的字段
        series.pop('金融资产合计', None)
        series.pop('息前税后经营利润', None)
        series.pop('净利润', None)
    
    def _add_asset_efficiency_calculations(self, chart: Dict, balance_df: pd.DataFrame, income_df: pd.DataFrame, date_columns: List[str]):
        """
        为经营资产效率图表添加计算字段
        
        Args:
            chart: 图表配置字典
            balance_df: 资产负债表数据DataFrame
            income_df: 利润表数据DataFrame
            date_columns: 日期列列表
        """
        data = chart['data']
        series = data['series']
        
        # 从资产负债表提取数据
        balance_data = self._extract_chart_data(balance_df, date_columns, {
            'bar': ['经营资产合计', '长期经营资产合计', '固定资产']
        })
        series.update(balance_data['series'])
        
        # 从利润表提取营业收入
        income_data = self._extract_chart_data(income_df, date_columns, {
            'bar': ['营业收入']
        })
        series.update(income_data['series'])
        
        # 提取需要的数据
        经营资产合计 = series.get('经营资产合计', {}).get('data', [])
        长期经营资产合计 = series.get('长期经营资产合计', {}).get('data', [])
        固定资产 = series.get('固定资产', {}).get('data', [])
        营业收入 = series.get('营业收入', {}).get('data', [])
        
        # 计算周转率
        经营资产周转率_data = []
        长期经营资产周转率_data = []
        固定资产周转率_data = []
        
        for i in range(len(date_columns)):
            revenue = 营业收入[i] if i < len(营业收入) and 营业收入[i] is not None else 0
            
            # 经营资产周转率 = 营业收入 / 经营资产合计
            operating_asset = 经营资产合计[i] if i < len(经营资产合计) and 经营资产合计[i] is not None else 0
            if operating_asset != 0:
                经营资产周转率_data.append(round(revenue / operating_asset, 1))
            else:
                经营资产周转率_data.append(None)
            
            # 长期经营资产周转率 = 营业收入 / 长期经营资产合计
            long_term_asset = 长期经营资产合计[i] if i < len(长期经营资产合计) and 长期经营资产合计[i] is not None else 0
            if long_term_asset != 0:
                长期经营资产周转率_data.append(round(revenue / long_term_asset, 1))
            else:
                长期经营资产周转率_data.append(None)
            
            # 固定资产周转率 = 营业收入 / 固定资产
            fixed_asset = 固定资产[i] if i < len(固定资产) and 固定资产[i] is not None else 0
            if fixed_asset != 0:
                固定资产周转率_data.append(round(revenue / fixed_asset, 1))
            else:
                固定资产周转率_data.append(None)
        
        # 添加计算字段到series
        series['经营资产周转率'] = {'type': 'line', 'data': 经营资产周转率_data}
        series['长期经营资产周转率'] = {'type': 'line', 'data': 长期经营资产周转率_data}
        series['固定资产周转率'] = {'type': 'line', 'data': 固定资产周转率_data}
        
        # 移除不需要在图表中显示的字段
        series.pop('经营资产合计', None)
        series.pop('长期经营资产合计', None)
        series.pop('固定资产', None)
        series.pop('营业收入', None)
    
    def _add_turnover_days_calculations(self, chart: Dict, balance_df: pd.DataFrame, income_df: pd.DataFrame, date_columns: List[str]):
        """
        为周转天数及营业周期图表添加计算字段
        
        Args:
            chart: 图表配置字典
            balance_df: 资产负债表数据DataFrame
            income_df: 利润表数据DataFrame
            date_columns: 日期列列表
        """
        data = chart['data']
        series = data['series']
        
        # 从资产负债表提取数据
        balance_data = self._extract_chart_data(balance_df, date_columns, {
            'bar': ['应收票据', '应收账款', '预收款项', '合同负债', '存货', '应付票据', '应付账款', '预付款项']
        })
        series.update(balance_data['series'])
        
        # 从利润表提取营业收入和营业成本
        income_data = self._extract_chart_data(income_df, date_columns, {
            'bar': ['营业收入', '营业成本']
        })
        series.update(income_data['series'])
        
        # 提取需要的数据
        应收票据 = series.get('应收票据', {}).get('data', [])
        应收账款 = series.get('应收账款', {}).get('data', [])
        预收款项 = series.get('预收款项', {}).get('data', [])
        合同负债 = series.get('合同负债', {}).get('data', [])
        存货 = series.get('存货', {}).get('data', [])
        应付票据 = series.get('应付票据', {}).get('data', [])
        应付账款 = series.get('应付账款', {}).get('data', [])
        预付款项 = series.get('预付款项', {}).get('data', [])
        营业收入 = series.get('营业收入', {}).get('data', [])
        营业成本 = series.get('营业成本', {}).get('data', [])
        
        # 计算周转天数
        应收账款周转天数_data = []
        存货周转天数_data = []
        应付账款周转天数_data = []
        营业周期_data = []
        现金周期_data = []
        
        for i in range(len(date_columns)):
            revenue = 营业收入[i] if i < len(营业收入) and 营业收入[i] is not None else 0
            
            # 应收账款周转率 = ((应收票据+应收账款)当期和上一期的均值 - 预收款项当期和上一期的均值) / 当期营业收入
            if i > 0:
                # 当期
                receivable_current = (应收票据[i] if i < len(应收票据) and 应收票据[i] is not None else 0) + \
                                   (应收账款[i] if i < len(应收账款) and 应收账款[i] is not None else 0)
                # 预收款项：优先使用预收款项，如果为空则使用合同负债（新会计准则）
                预收_current = 预收款项[i] if i < len(预收款项) and 预收款项[i] is not None else 0
                if 预收_current == 0:
                    预收_current = 合同负债[i] if i < len(合同负债) and 合同负债[i] is not None else 0
                
                # 前期
                receivable_prev = (应收票据[i-1] if i-1 < len(应收票据) and 应收票据[i-1] is not None else 0) + \
                                (应收账款[i-1] if i-1 < len(应收账款) and 应收账款[i-1] is not None else 0)
                预收_prev = 预收款项[i-1] if i-1 < len(预收款项) and 预收款项[i-1] is not None else 0
                if 预收_prev == 0:
                    预收_prev = 合同负债[i-1] if i-1 < len(合同负债) and 合同负债[i-1] is not None else 0
                
                # 平均值：应收款项-预收账款
                avg_receivable = (receivable_current + receivable_prev) / 2
                avg_advance = (预收_current + 预收_prev) / 2
                net_receivable = avg_receivable - avg_advance
                
                if revenue != 0 and net_receivable != 0:
                    应收账款周转率 = revenue / net_receivable
                    应收账款周转天数_data.append(round(365 / 应收账款周转率, 1))
                else:
                    应收账款周转天数_data.append(None)
                
                # 存货周转率 = 营业成本 / 平均存货（标准财务分析方法）
                inventory_current = 存货[i] if i < len(存货) and 存货[i] is not None else 0
                inventory_prev = 存货[i-1] if i-1 < len(存货) and 存货[i-1] is not None else 0
                avg_inventory = (inventory_current + inventory_prev) / 2
                cogs = 营业成本[i] if i < len(营业成本) and 营业成本[i] is not None else 0
                
                if cogs != 0 and avg_inventory != 0:
                    存货周转率 = cogs / avg_inventory
                    存货周转天数_data.append(round(365 / 存货周转率, 1))
                else:
                    存货周转天数_data.append(None)
                
                # 应付账款周转率 = ((应付票据 + 应付账款)当期和上一期的均值 - 预付款项当期和上一期的均值) / 当期营业收入
                payable_current = (应付票据[i] if i < len(应付票据) and 应付票据[i] is not None else 0) + \
                                (应付账款[i] if i < len(应付账款) and 应付账款[i] is not None else 0)
                prepaid_current = 预付款项[i] if i < len(预付款项) and 预付款项[i] is not None else 0
                
                payable_prev = (应付票据[i-1] if i-1 < len(应付票据) and 应付票据[i-1] is not None else 0) + \
                             (应付账款[i-1] if i-1 < len(应付账款) and 应付账款[i-1] is not None else 0)
                prepaid_prev = 预付款项[i-1] if i-1 < len(预付款项) and 预付款项[i-1] is not None else 0
                
                avg_payable = (payable_current + payable_prev) / 2
                avg_prepaid = (prepaid_current + prepaid_prev) / 2
                net_payable = avg_payable - avg_prepaid
                
                if revenue != 0 and net_payable != 0:
                    应付账款周转率 = revenue / net_payable
                    应付账款周转天数_data.append(round(365 / 应付账款周转率, 1))
                else:
                    应付账款周转天数_data.append(None)
                
                # 营业周期 = 应收账款周转天数 + 存货周转天数
                if 应收账款周转天数_data[-1] is not None and 存货周转天数_data[-1] is not None:
                    营业周期_data.append(round(应收账款周转天数_data[-1] + 存货周转天数_data[-1], 1))
                else:
                    营业周期_data.append(None)
                
                # 现金周期 = 营业周期 - 应付账款周转天数
                if 营业周期_data[-1] is not None and 应付账款周转天数_data[-1] is not None:
                    现金周期_data.append(round(营业周期_data[-1] - 应付账款周转天数_data[-1], 1))
                else:
                    现金周期_data.append(None)
            else:
                应收账款周转天数_data.append(None)
                存货周转天数_data.append(None)
                应付账款周转天数_data.append(None)
                营业周期_data.append(None)
                现金周期_data.append(None)
        
        # 添加计算字段到series
        series['应收账款周转天数'] = {'type': 'line', 'data': 应收账款周转天数_data}
        series['存货周转天数'] = {'type': 'line', 'data': 存货周转天数_data}
        series['应付账款周转天数'] = {'type': 'line', 'data': 应付账款周转天数_data}
        series['营业周期'] = {'type': 'line', 'data': 营业周期_data}
        series['现金周期'] = {'type': 'line', 'data': 现金周期_data}
        
        # 移除中间计算字段，只保留最终指标
        series.pop('应收票据', None)
        series.pop('应收账款', None)
        series.pop('预收款项', None)
        series.pop('合同负债', None)
        series.pop('存货', None)
        series.pop('应付票据', None)
        series.pop('应付账款', None)
        series.pop('预付款项', None)
        series.pop('营业收入', None)
        series.pop('营业成本', None)
    
    def _add_turnover_ratio_calculations(self, chart: Dict, balance_df: pd.DataFrame, income_df: pd.DataFrame, date_columns: List[str]):
        """
        为经营周转率图表添加计算字段
        
        Args:
            chart: 图表配置字典
            balance_df: 资产负债表数据DataFrame
            income_df: 利润表数据DataFrame
            date_columns: 日期列列表
        """
        data = chart['data']
        series = data['series']
        
        # 从资产负债表提取数据
        balance_data = self._extract_chart_data(balance_df, date_columns, {
            'bar': ['应收票据', '应收账款', '预收款项', '合同负债', '存货', '应付票据', '应付账款', '预付款项', '经营资产合计']
        })
        series.update(balance_data['series'])
        
        # 从利润表提取营业收入和营业成本
        income_data = self._extract_chart_data(income_df, date_columns, {
            'bar': ['营业收入', '营业成本']
        })
        series.update(income_data['series'])
        
        # 提取需要的数据
        应收票据 = series.get('应收票据', {}).get('data', [])
        应收账款 = series.get('应收账款', {}).get('data', [])
        预收款项 = series.get('预收款项', {}).get('data', [])
        合同负债 = series.get('合同负债', {}).get('data', [])
        存货 = series.get('存货', {}).get('data', [])
        应付票据 = series.get('应付票据', {}).get('data', [])
        应付账款 = series.get('应付账款', {}).get('data', [])
        预付款项 = series.get('预付款项', {}).get('data', [])
        经营资产合计 = series.get('经营资产合计', {}).get('data', [])
        营业收入 = series.get('营业收入', {}).get('data', [])
        营业成本 = series.get('营业成本', {}).get('data', [])
        
        # 计算周转率
        应收账款周转率_data = []
        存货周转率_data = []
        应付账款周转率_data = []
        经营资产周转率_data = []
        
        for i in range(len(date_columns)):
            revenue = 营业收入[i] if i < len(营业收入) and 营业收入[i] is not None else 0
            
            if i > 0:
                # 应收账款周转率
                receivable_current = (应收票据[i] if i < len(应收票据) and 应收票据[i] is not None else 0) + \
                                   (应收账款[i] if i < len(应收账款) and 应收账款[i] is not None else 0)
                # 预收款项：优先使用预收款项，如果为空则使用合同负债（新会计准则）
                预收_current = 预收款项[i] if i < len(预收款项) and 预收款项[i] is not None else 0
                if 预收_current == 0:
                    预收_current = 合同负债[i] if i < len(合同负债) and 合同负债[i] is not None else 0
                
                receivable_prev = (应收票据[i-1] if i-1 < len(应收票据) and 应收票据[i-1] is not None else 0) + \
                                (应收账款[i-1] if i-1 < len(应收账款) and 应收账款[i-1] is not None else 0)
                预收_prev = 预收款项[i-1] if i-1 < len(预收款项) and 预收款项[i-1] is not None else 0
                if 预收_prev == 0:
                    预收_prev = 合同负债[i-1] if i-1 < len(合同负债) and 合同负债[i-1] is not None else 0
                
                avg_receivable = (receivable_current + receivable_prev) / 2
                avg_advance = (预收_current + 预收_prev) / 2
                net_receivable = avg_receivable - avg_advance
                
                if net_receivable != 0:
                    应收账款周转率_data.append(round(revenue / net_receivable, 1))
                else:
                    应收账款周转率_data.append(None)
                
                # 存货周转率 = 营业成本 / 平均存货（标准财务分析方法）
                inventory_current = 存货[i] if i < len(存货) and 存货[i] is not None else 0
                inventory_prev = 存货[i-1] if i-1 < len(存货) and 存货[i-1] is not None else 0
                avg_inventory = (inventory_current + inventory_prev) / 2
                cogs = 营业成本[i] if i < len(营业成本) and 营业成本[i] is not None else 0
                
                if cogs != 0 and avg_inventory != 0:
                    存货周转率_data.append(round(cogs / avg_inventory, 1))
                else:
                    存货周转率_data.append(None)
                
                # 应付账款周转率
                payable_current = (应付票据[i] if i < len(应付票据) and 应付票据[i] is not None else 0) + \
                                (应付账款[i] if i < len(应付账款) and 应付账款[i] is not None else 0)
                prepaid_current = 预付款项[i] if i < len(预付款项) and 预付款项[i] is not None else 0
                
                payable_prev = (应付票据[i-1] if i-1 < len(应付票据) and 应付票据[i-1] is not None else 0) + \
                             (应付账款[i-1] if i-1 < len(应付账款) and 应付账款[i-1] is not None else 0)
                prepaid_prev = 预付款项[i-1] if i-1 < len(预付款项) and 预付款项[i-1] is not None else 0
                
                avg_payable = (payable_current + payable_prev) / 2
                avg_prepaid = (prepaid_current + prepaid_prev) / 2
                net_payable = avg_payable - avg_prepaid
                
                if net_payable != 0:
                    应付账款周转率_data.append(round(revenue / net_payable, 1))
                else:
                    应付账款周转率_data.append(None)
                
                # 经营资产周转率
                operating_asset = 经营资产合计[i] if i < len(经营资产合计) and 经营资产合计[i] is not None else 0
                if operating_asset != 0:
                    经营资产周转率_data.append(round(revenue / operating_asset, 1))
                else:
                    经营资产周转率_data.append(None)
            else:
                应收账款周转率_data.append(None)
                存货周转率_data.append(None)
                应付账款周转率_data.append(None)
                经营资产周转率_data.append(None)
        
        # 添加计算字段到series
        series['应收账款周转率'] = {'type': 'line', 'data': 应收账款周转率_data}
        series['存货周转率'] = {'type': 'line', 'data': 存货周转率_data}
        series['应付账款周转率'] = {'type': 'line', 'data': 应付账款周转率_data}
        series['经营资产周转率'] = {'type': 'line', 'data': 经营资产周转率_data}
        
        # 移除中间计算字段，只保留最终指标
        series.pop('应收票据', None)
        series.pop('应收账款', None)
        series.pop('预收款项', None)
        series.pop('合同负债', None)
        series.pop('存货', None)
        series.pop('应付票据', None)
        series.pop('应付账款', None)
        series.pop('预付款项', None)
        series.pop('经营资产合计', None)
        series.pop('营业收入', None)
        series.pop('营业成本', None)
    
    def _generate_finance_cost_charts(self, income_df: pd.DataFrame, date_columns: List[str]) -> List[Dict]:
        """生成财务成本分析图表配置"""
        charts = []
        
        # 图表1: 财务成本负担率
        chart1 = {
            'id': 'chart_finance_cost_burden',
            'title': '财务成本负担率',
            'type': 'bar_line',
            'data': {'dates': date_columns, 'series': {}},
            'colors': {
                '真实财务费用': self.COLORS['blue'],
                '税前利润': self.COLORS['orange'],
                '财务成本负担率': self.COLORS['gray']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent',
            'needs_finance_cost_calc': True
        }
        charts.append(chart1)
        
        return charts
    
    def _add_finance_cost_calculations(self, chart: Dict, income_df: pd.DataFrame, date_columns: List[str]):
        """
        为财务成本负担率图表添加计算字段
        
        财务成本负担率 = 1 - 税前利润 / 息税前利润总额
        """
        series = chart['data']['series']
        
        # 从利润表提取数据
        income_data = self._extract_chart_data(income_df, date_columns, {
            'bar': ['真实财务费用', '税前利润', '息税前利润总额']
        })
        
        # 添加柱状图数据
        series.update(income_data['series'])
        
        # 获取数据
        税前利润 = series.get('税前利润', {}).get('data', [])
        息税前利润总额 = series.get('息税前利润总额', {}).get('data', [])
        
        # 计算财务成本负担率
        财务成本负担率_data = []
        
        for i in range(len(date_columns)):
            ebt = 税前利润[i] if i < len(税前利润) and 税前利润[i] is not None else 0
            ebit = 息税前利润总额[i] if i < len(息税前利润总额) and 息税前利润总额[i] is not None else 0
            
            if ebit != 0:
                ratio = 1 - (ebt / ebit)
                财务成本负担率_data.append(round(ratio * 100, 2))  # 转换为百分比数值（乘以100），保留2位小数
            else:
                财务成本负担率_data.append(None)
        
        # 添加财务成本负担率折线
        series['财务成本负担率'] = {'type': 'line', 'data': 财务成本负担率_data}
        
        # 移除息税前利润总额（不在图例中显示）
        series.pop('息税前利润总额', None)
    
    def _generate_capex_charts(self, balance_df: pd.DataFrame, cashflow_df: pd.DataFrame, date_columns: List[str]) -> List[Dict]:
        """生成长期资产投资和并购活动分析图表配置"""
        charts = []
        
        # 图表1: 长期经营资产投资和并购活动分析
        chart1 = {
            'id': 'chart_capex_analysis',
            'title': '长期经营资产投资和并购活动分析',
            'type': 'bar_line',
            'data': {'dates': date_columns, 'series': {}},
            'colors': {
                '资本支出净额': self.COLORS['gray'],
                '扩张性资本支出': self.COLORS['orange'],
                '长期经营资产合计': self.COLORS['dark_gray'],
                '扩张性资本支出占长期资产期初净额的比例': self.COLORS['yellow']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent',
            'needs_capex_calc': True
        }
        charts.append(chart1)
        
        return charts
    
    def _add_capex_calculations(self, chart: Dict, balance_df: pd.DataFrame, cashflow_df: pd.DataFrame, date_columns: List[str]):
        """
        为长期资产投资和并购活动分析图表添加数据
        
        资本支出净额 = 长期经营资产净投资额 + 净合并额
        扩张性资本支出 = 长期经营资产扩张性资本支出 + 净合并额（现金流量表中已计算）
        扩张性资本支出占长期资产期初净额的比例（现金流量表中已计算）
        """
        series = chart['data']['series']
        
        # 从现金流量表提取数据（包括已计算的扩张性资本支出和占比）
        cashflow_data = self._extract_chart_data(cashflow_df, date_columns, {
            'bar': ['长期经营资产净投资额', '净合并额', '扩张性资本支出']
        })
        
        # 从资产负债表提取长期经营资产合计
        balance_data = self._extract_chart_data(balance_df, date_columns, {
            'bar': ['长期经营资产合计']
        })
        
        # 获取基础数据
        长期经营资产净投资额 = cashflow_data['series'].get('长期经营资产净投资额', {}).get('data', [])
        净合并额 = cashflow_data['series'].get('净合并额', {}).get('data', [])
        
        # 计算资本支出净额 = 长期经营资产净投资额 + 净合并额
        资本支出净额_data = []
        for i in range(len(date_columns)):
            net_invest = 长期经营资产净投资额[i] if i < len(长期经营资产净投资额) and 长期经营资产净投资额[i] is not None else 0
            merger = 净合并额[i] if i < len(净合并额) and 净合并额[i] is not None else 0
            资本支出净额_data.append(net_invest + merger if (net_invest != 0 or merger != 0) else None)
        
        # 从现金流量表中读取已计算好的扩张性资本支出占比（需要转换为百分比）
        扩张性资本支出占比_row = cashflow_df[cashflow_df['项目'] == '扩张性资本支出占长期资产期初净额的比例']
        扩张性资本支出占比_data = []
        
        if len(扩张性资本支出占比_row) > 0:
            for col in date_columns:
                if col in cashflow_df.columns:
                    val = 扩张性资本支出占比_row[col].values[0]
                    if pd.notna(val):
                        # 转换为百分比
                        扩张性资本支出占比_data.append(round(float(val) * 100, 2))
                    else:
                        扩张性资本支出占比_data.append(None)
                else:
                    扩张性资本支出占比_data.append(None)
        else:
            # 如果没有找到，填充None
            扩张性资本支出占比_data = [None] * len(date_columns)
        
        # 添加柱状图数据
        series['资本支出净额'] = {'type': 'bar', 'data': 资本支出净额_data}
        series['扩张性资本支出'] = cashflow_data['series']['扩张性资本支出']
        series['长期经营资产合计'] = balance_data['series']['长期经营资产合计']
        
        # 添加折线数据
        series['扩张性资本支出占长期资产期初净额的比例'] = {'type': 'line', 'data': 扩张性资本支出占比_data}
    
    def _generate_investment_income_charts(self, balance_df: pd.DataFrame, income_df: pd.DataFrame, date_columns: List[str]) -> List[Dict]:
        """生成投资收益分析图表配置"""
        charts = []
        
        # 图表1: 投资收益分析
        chart1 = {
            'id': 'chart_investment_income',
            'title': '投资收益',
            'type': 'stacked_bar_line',
            'data': {'dates': date_columns, 'series': {}},
            'colors': {
                '长期股权投资收益': self.COLORS['blue'],
                '长期股权外投资收益': self.COLORS['gray'],
                '长期股权投资收益率': self.COLORS['orange']
            },
            'y_axis_names': ['亿元', ''],
            'line_format': 'percent',
            'bar_format': 'decimal',  # 柱状图显示小数
            'show_values': True,  # 显示数值标签
            'needs_investment_income_calc': True
        }
        charts.append(chart1)
        
        return charts
    
    def _add_investment_income_calculations(self, chart: Dict, balance_df: pd.DataFrame, income_df: pd.DataFrame, date_columns: List[str]):
        """
        为投资收益分析图表添加数据
        
        长期股权投资收益：从利润表获取
        长期股权外投资收益 = 投资收益 - 长期股权投资收益
        长期股权投资收益率 = 长期股权投资收益 / 长期股权投资
        """
        series = chart['data']['series']
        
        # 从利润表提取数据
        income_data = self._extract_chart_data(income_df, date_columns, {
            'bar': ['长期股权投资收益', '投资收益']
        })
        
        # 从资产负债表提取长期股权投资
        balance_data = self._extract_chart_data(balance_df, date_columns, {
            'bar': ['长期股权投资']
        })
        
        # 获取基础数据
        长期股权投资收益 = income_data['series'].get('长期股权投资收益', {}).get('data', [])
        投资收益 = income_data['series'].get('投资收益', {}).get('data', [])
        长期股权投资 = balance_data['series'].get('长期股权投资', {}).get('data', [])
        
        # 计算长期股权外投资收益 = 投资收益 - 长期股权投资收益
        长期股权外投资收益_data = []
        for i in range(len(date_columns)):
            total_income = 投资收益[i] if i < len(投资收益) and 投资收益[i] is not None else 0
            equity_income = 长期股权投资收益[i] if i < len(长期股权投资收益) and 长期股权投资收益[i] is not None else 0
            other_income = total_income - equity_income
            # 只有当投资收益和长期股权投资收益都为None时才设为None
            if 投资收益[i] is None and 长期股权投资收益[i] is None:
                长期股权外投资收益_data.append(None)
            else:
                长期股权外投资收益_data.append(other_income)
        
        # 计算长期股权投资收益率 = 长期股权投资收益 / 长期股权投资
        长期股权投资收益率_data = []
        for i in range(len(date_columns)):
            equity_income = 长期股权投资收益[i] if i < len(长期股权投资收益) and 长期股权投资收益[i] is not None else 0
            equity_investment = 长期股权投资[i] if i < len(长期股权投资) and 长期股权投资[i] is not None else 0
            
            if equity_investment != 0:
                ratio = (equity_income / equity_investment) * 100  # 转换为百分比
                长期股权投资收益率_data.append(round(ratio, 2))
            else:
                长期股权投资收益率_data.append(None)
        
        # 添加柱状图数据
        series['长期股权投资收益'] = income_data['series']['长期股权投资收益']
        series['长期股权外投资收益'] = {'type': 'bar', 'data': 长期股权外投资收益_data}
        
        # 添加折线数据
        series['长期股权投资收益率'] = {'type': 'line', 'data': 长期股权投资收益率_data}
    
    def _extract_chart_data(
        self, 
        df: pd.DataFrame, 
        date_columns: List[str],
        series_config: Dict[str, List[str]]
    ) -> Dict:
        """
        从DataFrame中提取图表数据
        
        Args:
            df: 数据DataFrame
            date_columns: 日期列列表
            series_config: 系列配置，如 {'bar': ['字段1', '字段2'], 'line': ['字段3']}
            
        Returns:
            图表数据字典
        """
        result = {
            'dates': date_columns,
            'series': {}
        }
        
        # 判断字段是否为比率字段（需要乘以100）
        ratio_fields = ['毛利率', '净利润率', '营业成本率', '销售费用率', '管理费用率', '研发费用率', 
                       '营业税金及附加率', '资产减值损失率', '有息债务率', 
                       '息前税后经营利润率', '息税前经营利润率', '自由现金流/营业收入', '营业费用率',
                       '税金及附加率', '经营资产减值损失率', '营业外收支净额率', '总费用率']
        
        for chart_type, fields in series_config.items():
            for field in fields:
                # 查找字段对应的行
                field_row = df[df['项目'] == field]
                if len(field_row) > 0:
                    values = []
                    is_ratio = field in ratio_fields
                    
                    for date_col in date_columns:
                        if date_col in field_row.columns:
                            val = field_row[date_col].values[0]
                            # 转换为数值，处理NaN
                            if pd.notna(val):
                                if is_ratio:
                                    # 比率字段：乘以100转换为百分比
                                    values.append(float(val) * 100)
                                else:
                                    # 绝对值字段：转换为亿元（假设原始数据单位是元）
                                    values.append(float(val) / 100000000)
                            else:
                                values.append(None)
                        else:
                            values.append(None)
                    
                    result['series'][field] = {
                        'type': chart_type,
                        'data': values
                    }
        
        return result
    
    def _generate_html_template(self, charts_config: List[Dict], date_columns: List[str]) -> str:
        """生成HTML模板"""
        
        # 按类型分组图表
        balance_charts = []
        profit_charts = []
        efficiency_charts = []
        finance_cost_charts = []
        capex_charts = []
        investment_income_charts = []
        fcf_charts = []
        
        for chart in charts_config:
            if 'fcff' in chart['id'] or 'fcfe' in chart['id']:
                fcf_charts.append(chart)
            elif 'assets' in chart['id'] or 'capital' in chart['id'] or 'long_term' in chart['id'] or 'working_capital' in chart['id']:
                balance_charts.append(chart)
            elif 'revenue' in chart['id'] or 'ebit' in chart['id'] or 'operating_expenses' in chart['id']:
                profit_charts.append(chart)
            elif 'roic' in chart['id'] or 'efficiency' in chart['id'] or 'turnover' in chart['id']:
                efficiency_charts.append(chart)
            elif 'finance_cost' in chart['id']:
                finance_cost_charts.append(chart)
            elif 'capex' in chart['id']:
                capex_charts.append(chart)
            elif 'investment_income' in chart['id']:
                investment_income_charts.append(chart)
        
        # 生成各section的图表容器HTML
        def generate_section_charts(charts):
            html = ""
            for chart in charts:
                html += f'''
            <div class="chart-container">
                <div id="{chart['id']}" style="width: 100%; height: 500px;"></div>
            </div>
'''
            return html
        
        balance_containers = generate_section_charts(balance_charts)
        profit_containers = generate_section_charts(profit_charts)
        efficiency_containers = generate_section_charts(efficiency_charts)
        finance_cost_containers = generate_section_charts(finance_cost_charts)
        capex_containers = generate_section_charts(capex_charts)
        investment_income_containers = generate_section_charts(investment_income_charts)
        fcf_containers = generate_section_charts(fcf_charts)
        
        # 生成图表初始化JavaScript
        chart_scripts = ""
        for chart in charts_config:
            chart_scripts += self._generate_chart_script(chart) + "\n"
        
        # 完整HTML模板
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.company_name} ({self.stock_code}) 财务分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #5B9BD5;
        }}
        
        .header h1 {{
            font-size: 32px;
            color: #333;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 16px;
            color: #666;
        }}
        
        .section {{
            margin-bottom: 50px;
        }}
        
        .section-title {{
            font-size: 24px;
            color: #333;
            margin-bottom: 20px;
            padding-left: 15px;
            border-left: 4px solid #5B9BD5;
        }}
        
        .chart-container {{
            margin-bottom: 40px;
            padding: 20px;
            background-color: #fafafa;
            border-radius: 4px;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #999;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self.company_name} ({self.stock_code})</h1>
            <div class="subtitle">财务分析报告 | 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>
        
        <div class="section">
            <h2 class="section-title">一、资产负债分析</h2>
            {balance_containers}
        </div>
        
        <div class="section">
            <h2 class="section-title">二、利润分析</h2>
            {profit_containers}
        </div>
        
        <div class="section">
            <h2 class="section-title">三、经营效率分析</h2>
            {efficiency_containers}
        </div>
        
        <div class="section">
            <h2 class="section-title">四、财务成本分析</h2>
            {finance_cost_containers}
        </div>
        
        <div class="section">
            <h2 class="section-title">五、长期资产投资和并购活动分析</h2>
            {capex_containers}
        </div>
        
        <div class="section">
            <h2 class="section-title">六、投资收益分析</h2>
            {investment_income_containers}
        </div>
        
        <div class="section">
            <h2 class="section-title">七、自由现金流分析</h2>
            {fcf_containers}
        </div>
        
        <div class="footer">
            <p>本报告由财务分析系统自动生成 | 数据来源: Tushare</p>
        </div>
    </div>
    
    <script>
        // 图表初始化
        {chart_scripts}
        
        // 时间轴同步缩放 - 使用ECharts的connect功能
        var allCharts = [{', '.join([f"chart_{chart['id']}" for chart in charts_config])}];
        
        // 使用ECharts的group功能实现图表联动
        echarts.connect('financialReportGroup');
        allCharts.forEach(function(chart) {{
            chart.group = 'financialReportGroup';
        }});
        
        // 响应式调整
        window.addEventListener('resize', function() {{
            {self._generate_resize_script(charts_config)}
        }});
    </script>
</body>
</html>'''
        
        return html
    
    def _generate_chart_script(self, chart_config: Dict) -> str:
        """生成单个图表的ECharts配置脚本"""
        chart_id = chart_config['id']
        title = chart_config['title']
        chart_type = chart_config['type']
        data = chart_config['data']
        colors = chart_config.get('colors', {})
        y_axis_names = chart_config.get('y_axis_names', ['', ''])
        line_format = chart_config.get('line_format', 'value')
        bar_format = chart_config.get('bar_format', 'int')  # 柱状图格式：int或decimal
        show_values = chart_config.get('show_values', False)
        calculated_fields = chart_config.get('calculated_fields', {})
        
        # 处理计算字段
        for calc_field, (numerator, denominator) in calculated_fields.items():
            if numerator in data['series'] and denominator in data['series']:
                num_data = data['series'][numerator]['data']
                den_data = data['series'][denominator]['data']
                calc_data = []
                for i in range(len(num_data)):
                    if num_data[i] is not None and den_data[i] is not None and den_data[i] != 0:
                        # 计算比率并乘以100转换为百分比
                        calc_data.append((num_data[i] / den_data[i]) * 100)
                    else:
                        calc_data.append(None)
                
                data['series'][calc_field] = {
                    'type': 'line',
                    'data': calc_data
                }
        
        # 构建series配置
        series_list = []
        stack_config = chart_config.get('stack_config', {})
        
        # 创建字段到堆叠组的映射
        field_to_stack = {}
        for stack_name, fields in stack_config.items():
            for field in fields:
                field_to_stack[field] = stack_name
        
        for field_name, field_data in data['series'].items():
            series_type = field_data['type']
            field_values = field_data['data']
            
            series_item = {
                'name': field_name,
                'type': series_type,
                'data': field_values,
                'itemStyle': {'color': colors.get(field_name, self.COLORS['blue'])}
            }
            
            # 柱状图配置
            if series_type == 'bar':
                # 检查是否应该堆叠
                if chart_type == 'stacked_bar' or chart_type == 'stacked_bar_line':
                    series_item['stack'] = 'total'
                elif field_name in field_to_stack:
                    # 使用stack_config中定义的堆叠组
                    series_item['stack'] = field_to_stack[field_name]
                series_item['barMaxWidth'] = 50
                # 添加barGap和barCategoryGap配置
                bar_category_gap = chart_config.get('bar_category_gap', '20%')
                series_item['barGap'] = '5%'
                series_item['barCategoryGap'] = bar_category_gap
                if show_values:
                    # 根据bar_format选择格式化标记
                    formatter = '__FORMATTER_DECIMAL__' if bar_format == 'decimal' else '__FORMATTER_INT__'
                    series_item['label'] = {
                        'show': True,
                        'position': 'inside',
                        'formatter': formatter  # 标记，稍后替换为JS函数
                    }
            
            # 折线图配置
            elif series_type == 'line':
                series_item['yAxisIndex'] = 1
                series_item['lineStyle'] = {'width': 3}
                series_item['symbolSize'] = 8
                if line_format == 'percent':
                    series_item['label'] = {
                        'show': True,
                        'position': 'top',
                        'formatter': '__FORMATTER_PERCENT__'  # 标记，稍后替换为JS函数
                    }
                elif line_format == 'number':
                    series_item['label'] = {
                        'show': True,
                        'position': 'top',
                        'formatter': '__FORMATTER_DECIMAL__'  # 标记，稍后替换为JS函数（1位小数）
                    }
                else:
                    series_item['label'] = {
                        'show': True,
                        'position': 'top',
                        'formatter': '__FORMATTER_INT__'  # 标记，稍后替换为JS函数
                    }
            
            series_list.append(series_item)
        
        # 计算dataZoom的start值，默认显示最近10年
        total_dates = len(data['dates'])
        if total_dates <= 10:
            zoom_start = 0
        else:
            # 计算显示最后10个数据点的start百分比
            zoom_start = ((total_dates - 10) / total_dates) * 100
        
        # 生成JavaScript配置
        script = f'''
        var chart_{chart_id};
        (function() {{
            chart_{chart_id} = echarts.init(document.getElementById('{chart_id}'));
            var option_{chart_id} = {{
                title: {{
                    text: '{title}',
                    left: 'center',
                    textStyle: {{
                        fontSize: 18,
                        fontWeight: 'normal'
                    }}
                }},
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{
                        type: 'cross',
                        crossStyle: {{
                            color: '#999'
                        }}
                    }},
                    formatter: function(params) {{
                        var result = params[0].axisValue + '<br/>';
                        params.forEach(function(item) {{
                            var value = item.value;
                            var formattedValue;
                            // 判断是否为百分比系列（通过系列名称判断）
                            if (item.seriesName.includes('率') || item.seriesName.includes('比例')) {{
                                formattedValue = value != null ? value.toFixed(1) + '%' : '-';
                            }} else {{
                                formattedValue = value != null ? value.toFixed(0) : '-';
                            }}
                            result += item.marker + ' ' + item.seriesName + ': ' + formattedValue + '<br/>';
                        }});
                        return result;
                    }}
                }},
                legend: {{
                    data: {json.dumps(list(data['series'].keys()), ensure_ascii=False)},
                    bottom: 60,
                    textStyle: {{
                        fontSize: 12
                    }}
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
                    data: {json.dumps(data['dates'], ensure_ascii=False)},
                    axisPointer: {{
                        type: 'shadow'
                    }},
                    axisLabel: {{
                        rotate: 45,
                        fontSize: 11
                    }}
                }},
                yAxis: [
                    {{
                        type: 'value',
                        name: '{y_axis_names[0]}',
                        position: 'left',
                        axisLabel: {{
                            formatter: '{{value}}'
                        }}
                    }},
                    {{
                        type: 'value',
                        name: '{y_axis_names[1]}',
                        position: 'right',
                        axisLabel: {{
                            formatter: function(value) {{
                                return {'value.toFixed(1) + "%"' if line_format == 'percent' else 'value.toFixed(0)'};
                            }}
                        }}
                    }}
                ],
                series: {json.dumps(series_list, ensure_ascii=False)}
            }};
            
            // 替换formatter标记为真正的JavaScript函数
            option_{chart_id}.series.forEach(function(s) {{
                if (s.label && s.label.formatter) {{
                    if (s.label.formatter === '__FORMATTER_PERCENT__') {{
                        s.label.formatter = function(params) {{
                            return params.value != null ? params.value.toFixed(1) + '%' : '';
                        }};
                    }} else if (s.label.formatter === '__FORMATTER_DECIMAL__') {{
                        s.label.formatter = function(params) {{
                            return params.value != null ? params.value.toFixed(1) : '';
                        }};
                    }} else if (s.label.formatter === '__FORMATTER_INT__') {{
                        s.label.formatter = function(params) {{
                            return params.value != null ? params.value.toFixed(0) : '';
                        }};
                    }}
                }}
            }});
            
            chart_{chart_id}.setOption(option_{chart_id});
        }})();
        '''
        
        return script
    
    def _generate_resize_script(self, charts_config: List[Dict]) -> str:
        """生成图表响应式调整脚本"""
        resize_calls = []
        for chart in charts_config:
            resize_calls.append(f"echarts.init(document.getElementById('{chart['id']}')).resize();")
        return "\n            ".join(resize_calls)
    
    def _generate_fcf_charts(
        self,
        balance_df: pd.DataFrame,
        income_df: pd.DataFrame,
        cashflow_df: pd.DataFrame,
        date_columns: List[str]
    ) -> List[Dict]:
        """生成自由现金流分析图表配置（FCFF和FCFE）"""
        charts = []
        
        # 图表1: 根据EBIT计算的FCFF
        chart1 = self._generate_fcff_ebit_chart(balance_df, income_df, cashflow_df, date_columns)
        charts.append(chart1)
        
        # 图表2: FCFE vs Dividend
        chart2 = self._generate_fcfe_dividend_chart(balance_df, income_df, cashflow_df, date_columns)
        charts.append(chart2)
        
        return charts
    
    def _generate_fcff_ebit_chart(
        self,
        balance_df: pd.DataFrame,
        income_df: pd.DataFrame,
        cashflow_df: pd.DataFrame,
        date_columns: List[str]
    ) -> Dict:
        """生成根据EBIT计算的FCFF图表"""
        
        # 从利润表提取数据
        息税前经营利润_row = income_df[income_df['项目'] == '息税前经营利润']
        实际所得税税率_row = income_df[income_df['项目'] == '实际所得税税率']
        
        # 从现金流量表提取数据
        固定资产折旧_row = cashflow_df[cashflow_df['项目'] == '固定资产折旧、油气资产折耗、生产性生物资产折旧']
        无形资产摊销_row = cashflow_df[cashflow_df['项目'] == '无形资产摊销']
        长期待摊费用摊销_row = cashflow_df[cashflow_df['项目'] == '长期待摊费用摊销']
        处置损失_row = cashflow_df[cashflow_df['项目'] == '处置固定资产、无形资产和其他长期资产的损失']
        固定资产报废损失_row = cashflow_df[cashflow_df['项目'] == '固定资产报废损失']
        资本支出总额_row = cashflow_df[cashflow_df['项目'] == '资本支出总额']
        
        # 从资产负债表提取数据
        周转性经营投入_row = balance_df[balance_df['项目'] == '周转性经营投入合计']
        
        # 计算各项指标
        息税前经营利润税后_data = []
        折旧及摊销合计_data = []
        资本支出总额_data = []
        营运资本变化量_data = []
        FCFF_data = []
        
        for i, col in enumerate(date_columns):
            # 1. 息税前经营利润税后
            ebit = 息税前经营利润_row[col].values[0] if len(息税前经营利润_row) > 0 else 0
            tax_rate = 实际所得税税率_row[col].values[0] if len(实际所得税税率_row) > 0 else 0
            
            if pd.notna(ebit) and pd.notna(tax_rate):
                ebit_after_tax = float(ebit) * (1 - float(tax_rate))
                息税前经营利润税后_data.append(round(ebit_after_tax / 1e8, 0))
            else:
                ebit_after_tax = 0
                息税前经营利润税后_data.append(None)
            
            # 2. 折旧及摊销合计
            dep1 = 固定资产折旧_row[col].values[0] if len(固定资产折旧_row) > 0 else 0
            dep2 = 无形资产摊销_row[col].values[0] if len(无形资产摊销_row) > 0 else 0
            dep3 = 长期待摊费用摊销_row[col].values[0] if len(长期待摊费用摊销_row) > 0 else 0
            dep4 = 处置损失_row[col].values[0] if len(处置损失_row) > 0 else 0
            dep5 = 固定资产报废损失_row[col].values[0] if len(固定资产报废损失_row) > 0 else 0
            
            total_dep = 0
            for dep in [dep1, dep2, dep3, dep4, dep5]:
                if pd.notna(dep):
                    total_dep += float(dep)
            
            if total_dep != 0:
                折旧及摊销合计_data.append(round(total_dep / 1e8, 0))
            else:
                折旧及摊销合计_data.append(None)
            
            # 3. 资本支出
            capex = 资本支出总额_row[col].values[0] if len(资本支出总额_row) > 0 else 0
            if pd.notna(capex):
                资本支出总额_data.append(round(float(capex) / 1e8, 0))
            else:
                资本支出总额_data.append(None)
            
            # 4. 营运资本变化量（当期 - 上期，日期列是倒序的，所以上期是 i+1）
            current_wc = 周转性经营投入_row[col].values[0] if len(周转性经营投入_row) > 0 else 0
            if i < len(date_columns) - 1:
                prev_col = date_columns[i+1]
                prev_wc = 周转性经营投入_row[prev_col].values[0] if len(周转性经营投入_row) > 0 else 0
                if pd.notna(current_wc) and pd.notna(prev_wc):
                    wc_change = float(current_wc) - float(prev_wc)
                    营运资本变化量_data.append(round(wc_change / 1e8, 0))
                else:
                    wc_change = 0
                    营运资本变化量_data.append(None)
            else:
                wc_change = 0
                营运资本变化量_data.append(None)
            
            # 5. FCFF = 息税前经营利润税后 + 折旧摊销 - 资本支出 - 营运资本变化量
            fcff = ebit_after_tax + total_dep
            if pd.notna(capex):
                fcff -= float(capex)
            fcff -= wc_change
            FCFF_data.append(round(fcff / 1e8, 0))
        
        # 构建图表配置
        chart = {
            'id': 'chart_fcff_ebit',
            'title': '根据息税前经营利润计算的FCFF',
            'type': 'bar',
            'data': {
                'dates': date_columns,
                'series': {
                    '息税前经营利润': {
                        'type': 'bar',
                        'data': 息税前经营利润税后_data
                    },
                    '折旧及摊销合计': {
                        'type': 'bar',
                        'data': 折旧及摊销合计_data
                    },
                    '资本支出总额': {
                        'type': 'bar',
                        'data': 资本支出总额_data
                    },
                    '营运资本变化量': {
                        'type': 'bar',
                        'data': 营运资本变化量_data
                    },
                    'FCFF': {
                        'type': 'bar',
                        'data': FCFF_data
                    }
                }
            },
            'colors': {
                '息税前经营利润': '#70AD47',
                '折旧及摊销合计': '#FFC000',
                '资本支出总额': '#5B9BD5',
                '营运资本变化量': '#ED7D31',
                'FCFF': '#A5A5A5'
            },
            'bar_category_gap': '40%'  # 增加年度之间的间距
        }
        
        return chart
    
    def _generate_fcfe_dividend_chart(
        self,
        balance_df: pd.DataFrame,
        income_df: pd.DataFrame,
        cashflow_df: pd.DataFrame,
        date_columns: List[str]
    ) -> Dict:
        """生成FCFE vs Dividend图表"""
        
        # 从利润表提取数据
        净利润_row = income_df[income_df['项目'] == '净利润']
        
        # 从现金流量表提取数据
        固定资产折旧_row = cashflow_df[cashflow_df['项目'] == '固定资产折旧、油气资产折耗、生产性生物资产折旧']
        无形资产摊销_row = cashflow_df[cashflow_df['项目'] == '无形资产摊销']
        长期待摊费用摊销_row = cashflow_df[cashflow_df['项目'] == '长期待摊费用摊销']
        处置损失_row = cashflow_df[cashflow_df['项目'] == '处置固定资产、无形资产和其他长期资产的损失']
        固定资产报废损失_row = cashflow_df[cashflow_df['项目'] == '固定资产报废损失']
        资本支出总额_row = cashflow_df[cashflow_df['项目'] == '资本支出总额']
        
        # 从资产负债表提取数据
        周转性经营投入_row = balance_df[balance_df['项目'] == '周转性经营投入合计']
        有息债务_row = balance_df[balance_df['项目'] == '有息债务合计']
        
        # 计算FCFE
        FCFE_data = []
        
        for i, col in enumerate(date_columns):
            # 1. 净利润
            净利润 = 净利润_row[col].values[0] if len(净利润_row) > 0 else 0
            
            # 2. 折旧及摊销合计（包含5个项目）
            dep1 = 固定资产折旧_row[col].values[0] if len(固定资产折旧_row) > 0 else 0
            dep2 = 无形资产摊销_row[col].values[0] if len(无形资产摊销_row) > 0 else 0
            dep3 = 长期待摊费用摊销_row[col].values[0] if len(长期待摊费用摊销_row) > 0 else 0
            dep4 = 处置损失_row[col].values[0] if len(处置损失_row) > 0 else 0
            dep5 = 固定资产报废损失_row[col].values[0] if len(固定资产报废损失_row) > 0 else 0
            
            total_dep = 0
            for dep in [dep1, dep2, dep3, dep4, dep5]:
                if pd.notna(dep):
                    total_dep += float(dep)
            
            # 3. 资本支出总额
            capex = 资本支出总额_row[col].values[0] if len(资本支出总额_row) > 0 else 0
            
            # 4. 营运资本变化量（当期 - 上期，日期列是倒序的，所以上期是 i+1）
            current_wc = 周转性经营投入_row[col].values[0] if len(周转性经营投入_row) > 0 else 0
            if i < len(date_columns) - 1:
                prev_col = date_columns[i+1]
                prev_wc = 周转性经营投入_row[prev_col].values[0] if len(周转性经营投入_row) > 0 else 0
                if pd.notna(current_wc) and pd.notna(prev_wc):
                    wc_change = float(current_wc) - float(prev_wc)
                else:
                    wc_change = 0
            else:
                wc_change = 0
            
            # 5. 债务变化（当期 - 上期，日期列是倒序的，所以上期是 i+1）
            current_debt = 有息债务_row[col].values[0] if len(有息债务_row) > 0 else 0
            if i < len(date_columns) - 1:
                prev_col = date_columns[i+1]
                prev_debt = 有息债务_row[prev_col].values[0] if len(有息债务_row) > 0 else 0
                if pd.notna(current_debt) and pd.notna(prev_debt):
                    debt_change = float(current_debt) - float(prev_debt)
                else:
                    debt_change = 0
            else:
                debt_change = 0
            
            # 6. FCFE = 净利润 + 折旧摊销 - 资本支出 - 营运资本变化量 + 债务变化
            if pd.notna(净利润):
                fcfe = float(净利润) + total_dep
                if pd.notna(capex):
                    fcfe -= float(capex)
                fcfe -= wc_change
                fcfe += debt_change
                FCFE_data.append(round(fcfe / 1e8, 0))
            else:
                FCFE_data.append(None)
        
        # 读取分红数据
        分红_data = self._get_dividend_data(date_columns)
        
        # 构建图表配置
        chart = {
            'id': 'chart_fcfe_dividend',
            'title': '股权自由现金流VS分红',
            'type': 'line',
            'data': {
                'dates': date_columns,
                'series': {
                    'FCFE': {
                        'type': 'line',
                        'data': FCFE_data
                    },
                    '分红': {
                        'type': 'line',
                        'data': 分红_data
                    }
                }
            },
            'colors': {
                'FCFE': '#5470C6',
                '分红': '#EE6666'
            }
        }
        
        return chart
    
    def _get_dividend_data(self, date_columns: List[str]) -> List:
        """从数据库读取分红数据"""
        import os
        from financial_data_manager import FinancialDataManager
        
        try:
            # 从数据库读取分红数据
            db_manager = FinancialDataManager('database/financial_data.db')
            df = db_manager.get_dividend_data(self.stock_code)
            
            if df is None or len(df) == 0:
                return [None] * len(date_columns)
            
            # 确保列名正确
            if '报告期' in df.columns:
                df['end_date'] = df['报告期']
            elif 'end_date' not in df.columns:
                return [None] * len(date_columns)
            
            # 转换日期格式
            df['end_date'] = df['end_date'].astype(str)
            df['year'] = df['end_date'].str[:4]
            df['month'] = df['end_date'].str[4:6]
            
            # 优先使用税后派息，其次税前派息（直接使用中文列名）
            df['dividend'] = df.apply(
                lambda row: row.get('每股派息(税后)', 0) if pd.notna(row.get('每股派息(税后)')) and row.get('每股派息(税后)', 0) > 0 
                else (row.get('每股派息(税前)', 0) if pd.notna(row.get('每股派息(税前)')) else 0), 
                axis=1
            )
            
            # 去除重复记录
            df = df.sort_values('dividend', ascending=False).drop_duplicates(subset=['end_date'], keep='first')
            
            # 按年份汇总每股派息
            year_dividend_dict = {}
            year_q1q3_dividend_dict = {}
            
            for _, row in df.iterrows():
                year = row['year']
                month = row['month']
                cash_div = row['dividend']
                
                if cash_div > 0:
                    if year not in year_dividend_dict:
                        year_dividend_dict[year] = 0
                    year_dividend_dict[year] += cash_div
                    
                    if month in ['03', '06', '09']:
                        if year not in year_q1q3_dividend_dict:
                            year_q1q3_dividend_dict[year] = 0
                        year_q1q3_dividend_dict[year] += cash_div
            
            # 读取总股本数据
            balance_file = f'data/{self.stock_code}_balance_sheet_annual_ttm.csv'
            total_share_dict = {}
            
            if os.path.exists(balance_file):
                balance_df = pd.read_csv(balance_file, encoding='utf-8-sig')
                # 确保列名是字符串类型
                balance_df.columns = [str(col) for col in balance_df.columns]
                
                total_share_row = balance_df[balance_df['项目'] == '期末总股本']
                
                if len(total_share_row) > 0:
                    for col in date_columns:
                        if col in total_share_row.columns:
                            val = total_share_row[col].values[0]
                            if pd.notna(val):
                                total_share_dict[col] = val
            
            # 匹配日期列并计算分红总额
            dividend_data = []
            for col in date_columns:
                year = col[:4]
                is_ttm = 'TTM' in col or 'Q3' in col
                
                if is_ttm:
                    cash_div_per_share = year_q1q3_dividend_dict.get(year, 0)
                else:
                    cash_div_per_share = year_dividend_dict.get(year, 0)
                
                if cash_div_per_share > 0 and col in total_share_dict:
                    total_dividend = cash_div_per_share * total_share_dict[col]
                    dividend_data.append(round(total_dividend / 1e8, 0))
                else:
                    dividend_data.append(None)
            
            return dividend_data
        except Exception as e:
            print(f"读取分红数据失败: {e}")
            return [None] * len(date_columns)


if __name__ == '__main__':
    # 测试代码
    print("HTML报告生成器模块已加载")
    print("使用示例:")
    print("  generator = HTMLReportGenerator('美的集团', '000333.SZ')")
    print("  generator.generate_report(balance_data, income_data, cashflow_data)")
