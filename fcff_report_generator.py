#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自由现金流分析HTML报告生成器
"""

import pandas as pd
from typing import List, Dict
import json


class FCFFReportGenerator:
    """自由现金流分析HTML报告生成器"""
    
    # 配色方案（指定配色）
    COLORS = {
        'color1': '#FFA07A',  # 息税前经营利润 (浅珊瑚色)
        'color2': '#ADD8E6',  # 折旧及摊销合计 (浅蓝色)
        'color3': '#90EE90',  # 资本支出总额 (浅绿色)
        'color4': '#FFD700',  # 营运资本变化量 (金色)
        'color5': '#D3D3D3',  # FCFF (浅灰色)
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
        balance_df: pd.DataFrame,
        income_df: pd.DataFrame,
        cashflow_df: pd.DataFrame,
        output_path: str
    ) -> str:
        """
        生成自由现金流分析HTML报告
        
        Args:
            balance_df: 资产负债表数据
            income_df: 利润表数据
            cashflow_df: 现金流量表数据
            output_path: 输出文件路径
            
        Returns:
            生成的HTML文件路径
        """
        # 获取日期列
        date_columns = [col for col in balance_df.columns if col != '项目']
        
        # 生成图表配置
        charts_config = []
        
        # 图表1: 根据EBIT计算的FCFF
        chart1 = self._generate_fcff_ebit_chart(balance_df, income_df, cashflow_df, date_columns)
        charts_config.append(chart1)
        
        # 生成HTML内容
        html_content = self._generate_html_template(charts_config, date_columns)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ 自由现金流分析报告已生成: {output_path}")
        return output_path
    
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
            # 1. 息税前经营利润（显示原值）
            ebit = 息税前经营利润_row[col].values[0] if len(息税前经营利润_row) > 0 else 0
            tax_rate = 实际所得税税率_row[col].values[0] if len(实际所得税税率_row) > 0 else 0
            
            if pd.notna(ebit):
                ebit_value = float(ebit) / 1e8  # 转换为亿元
                息税前经营利润税后_data.append(round(ebit_value, 2))
                # 计算税后值用于FCFF计算
                if pd.notna(tax_rate):
                    ebit_after_tax = ebit_value * (1 - float(tax_rate))
                else:
                    ebit_after_tax = ebit_value
            else:
                ebit_after_tax = None
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
                折旧及摊销合计_data.append(round(total_dep / 1e8, 2))
            else:
                total_dep = None
                折旧及摊销合计_data.append(None)
            
            # 3. 资本支出总额
            capex = 资本支出总额_row[col].values[0] if len(资本支出总额_row) > 0 else 0
            if pd.notna(capex):
                资本支出总额_data.append(round(float(capex) / 1e8, 2))
            else:
                capex = None
                资本支出总额_data.append(None)
            
            # 4. 营运资本变化量
            current_wc = 周转性经营投入_row[col].values[0] if len(周转性经营投入_row) > 0 else 0
            if i > 0:
                prev_col = date_columns[i-1]
                prev_wc = 周转性经营投入_row[prev_col].values[0] if len(周转性经营投入_row) > 0 else 0
                if pd.notna(current_wc) and pd.notna(prev_wc):
                    wc_change = (float(current_wc) - float(prev_wc)) / 1e8
                    营运资本变化量_data.append(round(wc_change, 2))
                else:
                    wc_change = None
                    营运资本变化量_data.append(None)
            else:
                wc_change = None
                营运资本变化量_data.append(None)
            
            # 5. FCFF = 息税前经营利润×(1-实际所得税税率) + 折旧及摊销合计 - 资本支出总额 - 营运资本变化量
            if ebit_after_tax is not None:
                fcff = ebit_after_tax
                if total_dep is not None:
                    fcff += total_dep / 1e8
                if capex is not None:
                    fcff -= float(capex) / 1e8
                if wc_change is not None:
                    fcff -= wc_change
                FCFF_data.append(round(fcff, 2))
            else:
                FCFF_data.append(None)
        
        # 反转时间轴（从旧到新）
        date_columns_reversed = list(reversed(date_columns))
        息税前经营利润税后_data_reversed = list(reversed(息税前经营利润税后_data))
        折旧及摊销合计_data_reversed = list(reversed(折旧及摊销合计_data))
        资本支出总额_data_reversed = list(reversed(资本支出总额_data))
        营运资本变化量_data_reversed = list(reversed(营运资本变化量_data))
        FCFF_data_reversed = list(reversed(FCFF_data))
        
        # 构建图表配置
        chart = {
            'id': 'chart_fcff_ebit',
            'title': '根据息税前经营利润计算的FCFF',
            'dates': date_columns_reversed,
            'series': {
                '息税前经营利润': {
                    'type': 'bar',
                    'data': 息税前经营利润税后_data_reversed,
                    'color': self.COLORS['color1']
                },
                '折旧及摊销合计': {
                    'type': 'bar',
                    'data': 折旧及摊销合计_data_reversed,
                    'color': self.COLORS['color2']
                },
                '资本支出总额': {
                    'type': 'bar',
                    'data': 资本支出总额_data_reversed,
                    'color': self.COLORS['color3']
                },
                '营运资本变化量': {
                    'type': 'bar',
                    'data': 营运资本变化量_data_reversed,
                    'color': self.COLORS['color4']
                },
                'FCFF': {
                    'type': 'bar',
                    'data': FCFF_data_reversed,
                    'color': self.COLORS['color5']
                }
            }
        }
        
        return chart
    
    def _generate_html_template(self, charts_config: List[Dict], date_columns: List[str]) -> str:
        """生成HTML模板"""
        
        # 生成图表容器
        chart_containers = ""
        for chart in charts_config:
            chart_containers += f'''
            <div class="chart-container">
                <div id="{chart['id']}" style="width: 100%; height: 500px;"></div>
            </div>
'''
        
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
    <title>自由现金流分析报告 - {self.company_name} ({self.stock_code})</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f7fa;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .header p {{
            font-size: 16px;
            opacity: 0.9;
        }}
        
        .section {{
            padding: 40px;
        }}
        
        .section-title {{
            font-size: 24px;
            color: #333;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
            font-weight: 600;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>自由现金流分析报告</h1>
            <p>{self.company_name} ({self.stock_code})</p>
        </div>
        
        <div class="section">
            <h2 class="section-title">根据息税前经营利润计算的FCFF</h2>
            {chart_containers}
        </div>
        
        <div class="footer">
            <p>本报告由财务分析系统自动生成 | 数据来源: Tushare</p>
        </div>
    </div>
    
    <script>
        // 图表初始化
        {chart_scripts}
        
        // 响应式调整
        window.addEventListener('resize', function() {{
            {self._generate_resize_script(charts_config)}
        }});
    </script>
</body>
</html>
'''
        return html
    
    def _generate_chart_script(self, chart: Dict) -> str:
        """生成单个图表的ECharts配置脚本"""
        chart_id = chart['id']
        title = chart['title']
        dates = chart['dates']
        series_data = chart['series']
        
        # 构建series数组
        series_list = []
        for name, config in series_data.items():
            series_item = {
                'name': name,
                'type': config['type'],
                'data': config['data'],
                'itemStyle': {'color': config['color']},
                'barWidth': '12%',
                'barGap': '5%',
                'label': {
                    'show': True,
                    'position': 'inside',
                    'formatter': '{c}',
                    'fontSize': 10,
                    'color': '#666'
                }
            }
            series_list.append(series_item)
        
        # 转换为JSON
        series_json = json.dumps(series_list, ensure_ascii=False)
        dates_json = json.dumps(dates, ensure_ascii=False)
        
        script = f'''
        (function() {{
            var chart_{chart_id} = echarts.init(document.getElementById('{chart_id}'));
            var option_{chart_id} = {{
                title: {{
                    text: '{title}',
                    left: 'center',
                    textStyle: {{
                        fontSize: 18,
                        fontWeight: 'bold'
                    }}
                }},
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{
                        type: 'shadow'
                    }},
                    formatter: function(params) {{
                        let result = params[0].name + '<br/>';
                        params.forEach(function(item) {{
                            if (item.value != null) {{
                                result += item.marker + item.seriesName + ': ' + item.value.toFixed(0) + '亿元<br/>';
                            }}
                        }});
                        return result;
                    }}
                }},
                legend: {{
                    data: {json.dumps(list(series_data.keys()), ensure_ascii=False)},
                    top: 30,
                    left: 'center'
                }},
                grid: {{
                    left: '3%',
                    right: '4%',
                    bottom: '10%',
                    top: 80,
                    containLabel: true
                }},
                xAxis: {{
                    type: 'category',
                    data: {dates_json},
                    axisLabel: {{
                        rotate: 45,
                        interval: 0,
                        fontSize: 11
                    }},
                    axisTick: {{
                        alignWithLabel: true
                    }}
                }},
                barCategoryGap: '30%',
                yAxis: {{
                    type: 'value',
                    name: '亿元',
                    axisLabel: {{
                        formatter: '{{value}}'
                    }}
                }},
                series: {series_json}
            }};
            
            chart_{chart_id}.setOption(option_{chart_id});
        }})();
'''
        return script
    
    def _generate_resize_script(self, charts_config: List[Dict]) -> str:
        """生成图表响应式调整脚本"""
        resize_calls = []
        for chart in charts_config:
            chart_id = chart['id']
            resize_calls.append(f"echarts.getInstanceByDom(document.getElementById('{chart_id}')).resize();")
        return "\n            ".join(resize_calls)


if __name__ == '__main__':
    # 示例用法
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python fcff_report_generator.py <股票代码>")
        sys.exit(1)
    
    stock_code = sys.argv[1]
    
    # 读取数据
    balance_df = pd.read_csv(f'data/{stock_code}_balance_sheet_annual_ttm.csv', encoding='utf-8-sig')
    income_df = pd.read_csv(f'data/{stock_code}_income_statement_annual_ttm.csv', encoding='utf-8-sig')
    cashflow_df = pd.read_csv(f'data/{stock_code}_cashflow_statement_annual_ttm.csv', encoding='utf-8-sig')
    
    # 生成报告
    generator = FCFFReportGenerator(company_name="", stock_code=stock_code)
    output_path = f'data/{stock_code}_fcff_report.html'
    generator.generate_report(balance_df, income_df, cashflow_df, output_path)
