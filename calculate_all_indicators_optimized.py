"""
批量计算所有A股的核心指标并更新市场分布（优化版）
主要优化：
1. 批量写入数据库（每100只股票提交一次）
2. 使用事务减少I/O开销
3. 显示更详细的进度信息
"""

import logging
import sqlite3
from market_data_manager import MarketDataManager
from core_indicators_analyzer import CoreIndicatorsAnalyzer
from market_analyzer import MarketAnalyzer
from tqdm import tqdm
import time

# 配置日志
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def batch_save_indicators(conn, batch_data):
    """批量保存核心指标到数据库"""
    cursor = conn.cursor()
    
    for ts_code, end_date, indicators in batch_data:
        # 检查是否已存在
        existing = cursor.execute(
            "SELECT id FROM core_indicators WHERE ts_code = ? AND end_date = ?",
            (ts_code, end_date)
        ).fetchone()
        
        if existing:
            # 更新
            cursor.execute("""
                UPDATE core_indicators SET
                    ar_turnover_log = ?,
                    gross_margin = ?,
                    lta_turnover_log = ?,
                    working_capital_ratio = ?,
                    ocf_ratio = ?,
                    update_time = datetime('now')
                WHERE ts_code = ? AND end_date = ?
            """, (
                indicators.get('ar_turnover_log'),
                indicators.get('gross_margin'),
                indicators.get('lta_turnover_log'),
                indicators.get('working_capital_ratio'),
                indicators.get('ocf_ratio'),
                ts_code,
                end_date
            ))
        else:
            # 插入
            cursor.execute("""
                INSERT INTO core_indicators (
                    ts_code, end_date,
                    ar_turnover_log, gross_margin, lta_turnover_log,
                    working_capital_ratio, ocf_ratio,
                    update_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                ts_code, end_date,
                indicators.get('ar_turnover_log'),
                indicators.get('gross_margin'),
                indicators.get('lta_turnover_log'),
                indicators.get('working_capital_ratio'),
                indicators.get('ocf_ratio')
            ))
    
    conn.commit()

def main():
    print("="*80)
    print("批量计算所有A股的核心指标（优化版）")
    print("="*80)
    
    db = MarketDataManager('database/market_data.db')
    analyzer = CoreIndicatorsAnalyzer()
    
    # 获取所有股票列表
    conn = sqlite3.connect('database/market_data.db')
    cursor = conn.cursor()
    
    stocks = cursor.execute("SELECT ts_code, name FROM stock_list ORDER BY ts_code").fetchall()
    
    total_stocks = len(stocks)
    print(f"\n总共 {total_stocks} 只股票")
    print(f"优化策略：每100只股票批量提交一次数据库")
    
    success_count = 0
    failed_count = 0
    failed_stocks = []
    batch_data = []
    batch_size = 100
    
    start_time = time.time()
    print(f"\n开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("开始计算核心指标...\n")
    
    for idx, (ts_code, name) in enumerate(tqdm(stocks, desc="计算进度"), 1):
        try:
            # 获取财务数据
            balance = db.get_financial_data(ts_code, 'balancesheet')
            income = db.get_financial_data(ts_code, 'income')
            cashflow = db.get_financial_data(ts_code, 'cashflow')
            
            if balance is None or income is None or cashflow is None:
                failed_count += 1
                failed_stocks.append((ts_code, name, "数据不完整"))
                continue
            
            # 计算指标
            indicators = analyzer.calculate_all_indicators(balance, income, cashflow)
            
            if len(indicators) == 0:
                failed_count += 1
                failed_stocks.append((ts_code, name, "指标计算失败"))
                continue
            
            # 添加到批量数据
            for _, row in indicators.iterrows():
                indicator_dict = {
                    'ar_turnover_log': row.get('应收账款周转率对数'),
                    'gross_margin': row.get('毛利率'),
                    'lta_turnover_log': row.get('长期经营资产周转率对数'),
                    'working_capital_ratio': row.get('净营运资本比率'),
                    'ocf_ratio': row.get('经营现金流比率')
                }
                
                batch_data.append((
                    ts_code,
                    str(int(row['报告期'])),
                    indicator_dict
                ))
            
            success_count += 1
            
            # 每100只股票批量提交一次
            if idx % batch_size == 0:
                batch_save_indicators(conn, batch_data)
                batch_data = []
                
                # 显示进度统计
                elapsed = time.time() - start_time
                speed = idx / elapsed
                remaining = (total_stocks - idx) / speed if speed > 0 else 0
                
                print(f"\n进度: {idx}/{total_stocks} ({idx/total_stocks*100:.1f}%)")
                print(f"  成功: {success_count}, 失败: {failed_count}")
                print(f"  已用时: {elapsed/60:.1f}分钟, 预计剩余: {remaining/60:.1f}分钟")
                print(f"  速度: {speed:.2f} 只/秒\n")
            
        except Exception as e:
            failed_count += 1
            failed_stocks.append((ts_code, name, str(e)[:50]))
            continue
    
    # 保存剩余的批量数据
    if len(batch_data) > 0:
        batch_save_indicators(conn, batch_data)
    
    conn.close()
    
    elapsed_total = time.time() - start_time
    
    print(f"\n" + "="*80)
    print(f"计算完成！")
    print(f"="*80)
    print(f"  总耗时: {elapsed_total/60:.1f} 分钟")
    print(f"  成功: {success_count} 只")
    print(f"  失败: {failed_count} 只")
    print(f"  平均速度: {total_stocks/elapsed_total:.2f} 只/秒")
    
    if len(failed_stocks) > 0 and len(failed_stocks) <= 20:
        print(f"\n失败的股票:")
        for ts_code, name, reason in failed_stocks:
            print(f"  {ts_code} {name}: {reason}")
    elif len(failed_stocks) > 20:
        print(f"\n失败的股票（前20只）:")
        for ts_code, name, reason in failed_stocks[:20]:
            print(f"  {ts_code} {name}: {reason}")
    
    # 重新计算市场分布
    print("\n" + "="*80)
    print("重新计算市场分布")
    print("="*80)
    
    market_analyzer = MarketAnalyzer(db)
    results = market_analyzer.analyze_all_periods(exclude_outliers=True)
    
    print(f"\n✓ 成功分析 {len(results)} 个报告期的市场分布")
    
    # 显示最新报告期的市场分布
    if len(results) > 0:
        latest_period = list(results.keys())[-1]
        market_stats = market_analyzer.calculate_market_percentiles(latest_period)
        
        print(f"\n最新报告期 ({latest_period}) 市场分布:")
        print(f"  {'指标':<30} {'样本数':>8} {'均值':>10} {'中位数':>10}")
        print("  " + "-"*60)
        
        indicator_names = {
            'ar_turnover_log': '应收账款周转率对数',
            'gross_margin': '毛利率',
            'lta_turnover_log': '长期经营资产周转率对数',
            'working_capital_ratio': '净营运资本比率',
            'ocf_ratio': '经营现金流比率'
        }
        
        for col, name in indicator_names.items():
            if col in market_stats:
                stats = market_stats[col]
                print(f"  {name:<30} {stats['count']:>8} {stats['mean']:>10.2f} {stats['p50']:>10.2f}")
        
        # 检查毛利率是否合理
        if 'gross_margin' in market_stats:
            median = market_stats['gross_margin']['p50']
            if 20 <= median <= 40:
                print(f"\n✓ 毛利率中位数 {median:.2f}% 在合理范围内（20-40%）")
            else:
                print(f"\n⚠️  毛利率中位数 {median:.2f}% 可能需要检查")
    
    print("\n" + "="*80)
    print("全部完成！")
    print(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)


if __name__ == '__main__':
    main()
