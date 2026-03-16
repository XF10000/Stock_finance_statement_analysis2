"""
增强版股票分析报告生成器（包含可视化图表）
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from market_data_manager import MarketDataManager
from core_indicators_analyzer import CoreIndicatorsAnalyzer
from market_analyzer import MarketAnalyzer


class EnhancedReportGenerator:
    """增强版股票分析报告生成器"""
    
    def __init__(self, db_path: str = 'database/market_data.db'):
        """初始化报告生成器"""
        self.db = MarketDataManager(db_path)
        self.analyzer = CoreIndicatorsAnalyzer()
        self.market_analyzer = MarketAnalyzer(self.db)
        
        self.indicator_configs = {
            'ar_turnover_log': {
                'name': '应收账款周转率对数',
                'col': '应收账款周转率对数',
                'pct_col': 'ar_turnover_log_percentile',
                'color': '#1890ff'
            },
            'gross_margin': {
                'name': '毛利率',
                'col': '毛利率',
                'pct_col': 'gross_margin_percentile',
                'color': '#52c41a',
                'unit': '%'
            },
            'lta_turnover_log': {
                'name': '长期经营资产周转率对数',
                'col': '长期经营资产周转率对数',
                'pct_col': 'lta_turnover_log_percentile',
                'color': '#faad14'
            },
            'working_capital_ratio': {
                'name': '净营运资本比率',
                'col': '净营运资本比率',
                'pct_col': 'working_capital_ratio_percentile',
                'color': '#722ed1',
                'unit': '%'
            },
            'ocf_ratio': {
                'name': '经营现金流比率',
                'col': '经营现金流比率',
                'pct_col': 'ocf_ratio_percentile',
                'color': '#eb2f96',
                'unit': '%'
            }
        }
    
    def generate_report(self, ts_code: str, output_path: str = None):
        """
        生成单只股票的HTML分析报告（包含图表）
        
        Args:
            ts_code: 股票代码
            output_path: 输出文件路径
        """
        if output_path is None:
            output_path = f"docs/{ts_code.replace('.', '_')}_分析报告.html"
        
        print(f"正在生成 {ts_code} 的分析报告...")
        
        # 获取数据
        stock_info = self._get_stock_info(ts_code)
        balance = self.db.get_financial_data(ts_code, 'balancesheet')
        income = self.db.get_financial_data(ts_code, 'income')
        cashflow = self.db.get_financial_data(ts_code, 'cashflow')
        
        if balance is None or income is None or cashflow is None:
            raise ValueError(f"股票 {ts_code} 的财务数据不完整")
        
        # 计算指标
        indicators = self.analyzer.calculate_all_indicators(balance, income, cashflow)
        percentile_history = self.market_analyzer.get_stock_percentile_history(ts_code)
        
        # 生成图表HTML
        charts_html = self._generate_charts(indicators, percentile_history)
        
        # 生成完整HTML
        html = self._generate_html(stock_info, indicators, percentile_history, charts_html)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✓ 报告已生成: {output_path}")
        return output_path
    
    def _get_stock_info(self, ts_code: str):
        """获取股票基本信息"""
        import sqlite3
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
    
    def _generate_charts(self, indicators, percentile_history):
        """生成所有图表的HTML"""
        charts_html = ""
        
        # 为每个指标生成图表
        for key, config in self.indicator_configs.items():
            chart_html = self._generate_indicator_chart(
                indicators, 
                percentile_history,
                config
            )
            charts_html += chart_html
        
        return charts_html
    
    def _generate_indicator_chart(self, indicators, percentile_history, config):
        """生成单个指标的图表（指标值 + 分位数排名）"""
        
        # 创建子图：上方为指标值趋势，下方为分位数排名
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                f'{config["name"]}历史趋势',
                f'{config["name"]}全A股分位数排名'
            ),
            vertical_spacing=0.15,
            row_heights=[0.5, 0.5]
        )
        
        # 准备数据
        if len(indicators) > 0 and config['col'] in indicators.columns:
            periods = indicators['报告期'].astype(int).astype(str)
            values = indicators[config['col']]
            
            # 上图：指标值趋势
            fig.add_trace(
                go.Scatter(
                    x=periods,
                    y=values,
                    mode='lines+markers',
                    name=config['name'],
                    line=dict(color=config['color'], width=2),
                    marker=dict(size=6),
                    hovertemplate='%{x}<br>%{y:.2f}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # 下图：分位数排名
        if len(percentile_history) > 0 and config['pct_col'] in percentile_history.columns:
            pct_periods = percentile_history['end_date'].astype(int).astype(str)
            pct_values = percentile_history[config['pct_col']]
            
            # 根据分位数值设置颜色
            colors = []
            for val in pct_values:
                if pd.notna(val):
                    if val >= 75:
                        colors.append('#52c41a')  # 绿色
                    elif val >= 25:
                        colors.append('#faad14')  # 黄色
                    else:
                        colors.append('#f5222d')  # 红色
                else:
                    colors.append('#d9d9d9')  # 灰色
            
            fig.add_trace(
                go.Bar(
                    x=pct_periods,
                    y=pct_values,
                    name='分位数排名',
                    marker=dict(color=colors),
                    hovertemplate='%{x}<br>%{y:.1f}%<extra></extra>'
                ),
                row=2, col=1
            )
            
            # 添加参考线
            fig.add_hline(y=75, line_dash="dash", line_color="green", 
                         annotation_text="75%", row=2, col=1)
            fig.add_hline(y=50, line_dash="dash", line_color="gray", 
                         annotation_text="中位数", row=2, col=1)
            fig.add_hline(y=25, line_dash="dash", line_color="red", 
                         annotation_text="25%", row=2, col=1)
        
        # 更新布局
        unit = config.get('unit', '')
        fig.update_xaxes(title_text="报告期", row=1, col=1)
        fig.update_yaxes(title_text=f"{config['name']}{unit}", row=1, col=1)
        fig.update_xaxes(title_text="报告期", row=2, col=1)
        fig.update_yaxes(title_text="分位数 (%)", range=[0, 100], row=2, col=1)
        
        fig.update_layout(
            height=600,
            showlegend=False,
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family="PingFang SC, Microsoft YaHei, sans-serif")
        )
        
        # 转换为HTML
        chart_html = f"""
        <div class="chart-container">
            <h3>{config['name']}</h3>
            {fig.to_html(include_plotlyjs=False, div_id=f"chart_{config['name']}")}
            {self._get_indicator_analysis(config['name'])}
        </div>
        """
        
        return chart_html
    
    def _get_indicator_analysis(self, indicator_name):
        """获取指标的分析说明"""
        
        analyses = {
            '应收账款周转率对数': """
                <div class="analysis-text">
                    <h4>分析要点</h4>
                    <ul>
                        <li><strong>逻辑一致性检验</strong>：应收账款周转率下降可能意味着企业竞争力减弱或存在虚增收入风险</li>
                        <li><strong>与毛利率交叉验证</strong>：如果应收账款周转率下降但毛利率上升，需要合理解释这种不一致性</li>
                        <li><strong>分位数趋势</strong>：关注该指标在全A样本中的分位数变化，持续下降是负面信号</li>
                    </ul>
                </div>
            """,
            '毛利率': """
                <div class="analysis-text">
                    <h4>分析要点</h4>
                    <ul>
                        <li><strong>盈利能力指标</strong>：毛利率反映企业的定价能力和成本控制水平</li>
                        <li><strong>与周转率一致性</strong>：毛利率提升应与应收账款周转率改善同步，否则需警惕</li>
                        <li><strong>行业对比</strong>：关注毛利率在全A样本中的相对位置，判断竞争优势</li>
                    </ul>
                </div>
            """,
            '长期经营资产周转率对数': """
                <div class="analysis-text">
                    <h4>分析要点</h4>
                    <ul>
                        <li><strong>再投资质量</strong>：该指标反映长期资产的使用效率和再投资回报</li>
                        <li><strong>跑冒滴漏检验</strong>：周转率趋势性下降可能暗示资产质量问题或"三步循环法"造假</li>
                        <li><strong>竞争力验证</strong>：分位数持续上升意味着资产利用效率和产业竞争力改善</li>
                    </ul>
                </div>
            """,
            '净营运资本比率': """
                <div class="analysis-text">
                    <h4>分析要点</h4>
                    <ul>
                        <li><strong>产业链地位</strong>：负值表示占用上下游资金（地位强），正值表示被占用（地位弱）</li>
                        <li><strong>资金效率</strong>：该比率反映不能创造收益的在途资金占比</li>
                        <li><strong>龙头验证</strong>：如果公司定位为"龙头"，该指标分位数应持续下降或保持低位</li>
                    </ul>
                </div>
            """,
            '经营现金流比率': """
                <div class="analysis-text">
                    <h4>分析要点</h4>
                    <ul>
                        <li><strong>真实盈利能力</strong>：该指标相当于现金流版的ROA，反映真实的盈利质量</li>
                        <li><strong>市场基准</strong>：2024年全A样本中位数仅4.3%，高于此值说明盈利质量较好</li>
                        <li><strong>季节性特征</strong>：一季度通常回款较差，如果一季度该指标较高则尤为难得</li>
                    </ul>
                </div>
            """
        }
        
        return analyses.get(indicator_name, '')
    
    def _generate_html(self, stock_info, indicators, percentile_history, charts_html):
        """生成完整HTML"""
        
        latest_indicators = indicators.iloc[-1] if len(indicators) > 0 else None
        latest_percentile = percentile_history.iloc[-1] if len(percentile_history) > 0 else None
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{stock_info['name']} ({stock_info['ts_code']}) - 财务分析报告</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .header {{
            border-bottom: 3px solid #1890ff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: #1890ff;
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .meta {{
            color: #666;
            font-size: 14px;
        }}
        
        .meta span {{
            margin-right: 20px;
        }}
        
        h2 {{
            color: #333;
            font-size: 24px;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e8e8e8;
        }}
        
        h3 {{
            color: #1890ff;
            font-size: 20px;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        
        h4 {{
            color: #333;
            font-size: 16px;
            margin-top: 15px;
            margin-bottom: 10px;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .summary-card h3 {{
            font-size: 14px;
            color: rgba(255,255,255,0.9);
            margin-bottom: 10px;
        }}
        
        .summary-value {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .summary-percentile {{
            font-size: 14px;
            color: rgba(255,255,255,0.8);
        }}
        
        .chart-container {{
            margin: 40px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }}
        
        .analysis-text {{
            margin-top: 20px;
            padding: 15px;
            background: white;
            border-left: 4px solid #1890ff;
            border-radius: 4px;
        }}
        
        .analysis-text ul {{
            margin-left: 20px;
            margin-top: 10px;
        }}
        
        .analysis-text li {{
            margin-bottom: 8px;
            line-height: 1.8;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e8e8e8;
            text-align: center;
            color: #999;
            font-size: 12px;
        }}
        
        .na {{
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{stock_info['name']} ({stock_info['ts_code']})</h1>
            <div class="meta">
                <span>市场: {stock_info['market']}</span>
                <span>上市日期: {stock_info['list_date']}</span>
                <span>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
            </div>
        </div>
"""
        
        # 最新指标概览
        if latest_indicators is not None and latest_percentile is not None:
            html += f"""
        <h2>最新财务指标概览</h2>
        <div class="meta" style="margin-bottom: 20px;">
            报告期: {int(latest_indicators['报告期'])}
        </div>
        
        <div class="summary-grid">
"""
            
            for key, config in self.indicator_configs.items():
                value = latest_indicators.get(config['col'])
                percentile = latest_percentile.get(config['pct_col'])
                
                unit = config.get('unit', '')
                value_str = f"{value:.2f}{unit}" if pd.notna(value) else '<span class="na">N/A</span>'
                pct_str = f"全A排名: {percentile:.1f}%" if pd.notna(percentile) else "全A排名: N/A"
                
                html += f"""
            <div class="summary-card">
                <h3>{config['name']}</h3>
                <div class="summary-value">{value_str}</div>
                <div class="summary-percentile">{pct_str}</div>
            </div>
"""
            
            html += """
        </div>
"""
        
        # 添加图表
        html += f"""
        <h2>四大核心指标详细分析</h2>
        {charts_html}
"""
        
        # 页脚
        html += """
        <div class="footer">
            <p>本报告基于Tushare财务数据生成 | 数据仅供参考，不构成投资建议</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html


def main():
    """测试报告生成"""
    generator = EnhancedReportGenerator()
    
    # 生成美的集团的报告
    ts_code = '000333.SZ'
    output_path = generator.generate_report(ts_code)
    
    print(f"\n✓ 报告已生成: {output_path}")
    print(f"请在浏览器中打开查看")


if __name__ == '__main__':
    main()
