"""
单只股票HTML分析报告生成器
"""

import pandas as pd
from datetime import datetime
from market_data_manager import MarketDataManager
from core_indicators_analyzer import CoreIndicatorsAnalyzer
from market_analyzer import MarketAnalyzer


class StockReportGenerator:
    """股票分析报告生成器"""
    
    def __init__(self, db_path: str = 'database/market_data.db'):
        """初始化报告生成器"""
        self.db = MarketDataManager(db_path)
        self.analyzer = CoreIndicatorsAnalyzer()
        self.market_analyzer = MarketAnalyzer(self.db)
    
    def generate_report(self, ts_code: str, output_path: str = None):
        """
        生成单只股票的HTML分析报告
        
        Args:
            ts_code: 股票代码
            output_path: 输出文件路径，默认为 docs/{ts_code}_Report.html
        """
        if output_path is None:
            output_path = f"docs/{ts_code.replace('.', '_')}_Report.html"
        
        # 获取股票基本信息
        stock_info = self._get_stock_info(ts_code)
        
        # 获取财务数据
        balance = self.db.get_financial_data(ts_code, 'balancesheet')
        income = self.db.get_financial_data(ts_code, 'income')
        cashflow = self.db.get_financial_data(ts_code, 'cashflow')
        
        if balance is None or income is None or cashflow is None:
            raise ValueError(f"股票 {ts_code} 的财务数据不完整")
        
        # 计算核心指标
        indicators = self.analyzer.calculate_all_indicators(balance, income, cashflow)
        
        # 获取分位数排名历史
        percentile_history = self.market_analyzer.get_stock_percentile_history(ts_code)
        
        # 生成HTML
        html = self._generate_html(stock_info, indicators, percentile_history)
        
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
    
    def _generate_html(self, stock_info, indicators, percentile_history):
        """生成HTML内容"""
        
        # 获取最新一期数据
        latest_indicators = indicators.iloc[-1] if len(indicators) > 0 else None
        latest_percentile = percentile_history.iloc[-1] if len(percentile_history) > 0 else None
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{stock_info['name']} ({stock_info['ts_code']}) - 财务分析报告</title>
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
            max-width: 1200px;
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
        
        .indicator-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .indicator-card {{
            background: #fafafa;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #1890ff;
        }}
        
        .indicator-card h3 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }}
        
        .indicator-value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .indicator-percentile {{
            font-size: 14px;
            color: #52c41a;
            font-weight: 500;
        }}
        
        .percentile-high {{
            color: #52c41a;
        }}
        
        .percentile-medium {{
            color: #faad14;
        }}
        
        .percentile-low {{
            color: #f5222d;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        th, td {{
            padding: 12px;
            text-align: right;
            border-bottom: 1px solid #e8e8e8;
        }}
        
        th {{
            background: #fafafa;
            font-weight: 600;
            color: #333;
        }}
        
        th:first-child, td:first-child {{
            text-align: left;
        }}
        
        tr:hover {{
            background: #fafafa;
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
        
        <div class="indicator-grid">
"""
            
            indicators_config = [
                ('应收账款周转率对数', 'ar_turnover_log_percentile', '应收账款周转率对数'),
                ('毛利率', 'gross_margin_percentile', '毛利率 (%)'),
                ('长期经营资产周转率对数', 'lta_turnover_log_percentile', '长期经营资产周转率对数'),
                ('净营运资本比率', 'working_capital_ratio_percentile', '净营运资本比率 (%)'),
                ('经营现金流比率', 'ocf_ratio_percentile', '经营现金流比率 (%)')
            ]
            
            for ind_name, pct_col, display_name in indicators_config:
                value = latest_indicators.get(ind_name)
                percentile = latest_percentile.get(pct_col)
                
                if pd.notna(value):
                    value_str = f"{value:.2f}"
                else:
                    value_str = '<span class="na">N/A</span>'
                
                if pd.notna(percentile):
                    pct_str = f"{percentile:.1f}%"
                    if percentile >= 75:
                        pct_class = "percentile-high"
                    elif percentile >= 25:
                        pct_class = "percentile-medium"
                    else:
                        pct_class = "percentile-low"
                    pct_html = f'<div class="indicator-percentile {pct_class}">全A排名: {pct_str}</div>'
                else:
                    pct_html = '<div class="indicator-percentile na">全A排名: N/A</div>'
                
                html += f"""
            <div class="indicator-card">
                <h3>{display_name}</h3>
                <div class="indicator-value">{value_str}</div>
                {pct_html}
            </div>
"""
            
            html += """
        </div>
"""
        
        # 历史趋势表格
        if len(indicators) > 0:
            html += """
        <h2>历史财务指标趋势</h2>
        <table>
            <thead>
                <tr>
                    <th>报告期</th>
                    <th>应收账款周转率对数</th>
                    <th>毛利率 (%)</th>
                    <th>长期经营资产周转率对数</th>
                    <th>净营运资本比率 (%)</th>
                    <th>经营现金流比率 (%)</th>
                </tr>
            </thead>
            <tbody>
"""
            
            # 只显示最近10期
            recent_indicators = indicators.tail(10)
            
            for _, row in recent_indicators.iterrows():
                period = int(row['报告期'])
                
                def fmt_val(val):
                    return f"{val:.2f}" if pd.notna(val) else '<span class="na">N/A</span>'
                
                html += f"""
                <tr>
                    <td>{period}</td>
                    <td>{fmt_val(row.get('应收账款周转率对数'))}</td>
                    <td>{fmt_val(row.get('毛利率'))}</td>
                    <td>{fmt_val(row.get('长期经营资产周转率对数'))}</td>
                    <td>{fmt_val(row.get('净营运资本比率'))}</td>
                    <td>{fmt_val(row.get('经营现金流比率'))}</td>
                </tr>
"""
            
            html += """
            </tbody>
        </table>
"""
        
        # 分位数排名历史
        if len(percentile_history) > 0:
            html += """
        <h2>全A股分位数排名历史</h2>
        <table>
            <thead>
                <tr>
                    <th>报告期</th>
                    <th>应收账款周转率</th>
                    <th>毛利率</th>
                    <th>长期经营资产周转率</th>
                    <th>净营运资本比率</th>
                    <th>经营现金流比率</th>
                </tr>
            </thead>
            <tbody>
"""
            
            # 只显示最近10期
            recent_percentiles = percentile_history.tail(10)
            
            for _, row in recent_percentiles.iterrows():
                period = int(row['end_date'])
                
                def fmt_pct(val):
                    if pd.notna(val):
                        if val >= 75:
                            cls = "percentile-high"
                        elif val >= 25:
                            cls = "percentile-medium"
                        else:
                            cls = "percentile-low"
                        return f'<span class="{cls}">{val:.1f}%</span>'
                    return '<span class="na">N/A</span>'
                
                html += f"""
                <tr>
                    <td>{period}</td>
                    <td>{fmt_pct(row.get('ar_turnover_log_percentile'))}</td>
                    <td>{fmt_pct(row.get('gross_margin_percentile'))}</td>
                    <td>{fmt_pct(row.get('lta_turnover_log_percentile'))}</td>
                    <td>{fmt_pct(row.get('working_capital_ratio_percentile'))}</td>
                    <td>{fmt_pct(row.get('ocf_ratio_percentile'))}</td>
                </tr>
"""
            
            html += """
            </tbody>
        </table>
"""
        
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
    generator = StockReportGenerator()
    
    # 生成贵州茅台的报告
    ts_code = '600519.SH'
    output_path = generator.generate_report(ts_code)
    
    print(f"\n报告已生成: {output_path}")
    print(f"请在浏览器中打开查看")


if __name__ == '__main__':
    main()
