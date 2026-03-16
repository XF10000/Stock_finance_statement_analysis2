"""
简化版：重新计算所有股票的核心指标
使用MarketDataManager批量处理，优化数据库写入
"""
import sqlite3
import time
from datetime import datetime
from market_data_manager import MarketDataManager
from core_indicators_analyzer import CoreIndicatorsAnalyzer
from tqdm import tqdm

def main():
    print("="*80)
    print("批量重新计算所有股票的核心指标")
    print("="*80)
    
    db = MarketDataManager('database/market_data.db')
    analyzer = CoreIndicatorsAnalyzer()
    conn = db.get_connection()
    
    start_time = time.time()
    
    # 1. 获取所有股票列表
    print("\n步骤1：获取股票列表...")
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT ts_code FROM balancesheet ORDER BY ts_code')
    all_stocks = [row[0] for row in cursor.fetchall()]
    print(f"  找到 {len(all_stocks)} 只股票")
    
    # 2. 批量计算并写入
    print("\n步骤2：批量计算核心指标...")
    
    success_count = 0
    failed_count = 0
    failed_stocks = []
    all_insert_data = []
    
    for ts_code in tqdm(all_stocks, desc="计算进度"):
        try:
            # 获取财务数据
            balance = db.get_financial_data(ts_code, 'balancesheet')
            income = db.get_financial_data(ts_code, 'income')
            cashflow = db.get_financial_data(ts_code, 'cashflow')
            
            if len(balance) == 0 or len(income) == 0 or len(cashflow) == 0:
                failed_count += 1
                failed_stocks.append((ts_code, "缺少财务数据"))
                continue
            
            # 计算指标
            indicators = analyzer.calculate_all_indicators(balance, income, cashflow)
            
            if len(indicators) == 0:
                failed_count += 1
                failed_stocks.append((ts_code, "计算结果为空"))
                continue
            
            # 准备批量插入数据
            for _, row in indicators.iterrows():
                all_insert_data.append((
                    ts_code,
                    int(row['报告期']),
                    row.get('应收账款周转率'),
                    row.get('应收账款周转率对数'),
                    None,  # percentile稍后计算
                    row.get('毛利率'),
                    None,
                    row.get('长期经营资产周转率'),
                    row.get('长期经营资产周转率对数'),
                    None,
                    row.get('净营运资本比率'),
                    None,
                    row.get('经营现金流比率'),
                    None,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            success_count += 1
            
            # 每100只股票提交一次
            if success_count % 100 == 0:
                cursor.executemany('''
                    INSERT OR REPLACE INTO core_indicators (
                        ts_code, end_date,
                        ar_turnover, ar_turnover_log, ar_turnover_log_percentile,
                        gross_margin, gross_margin_percentile,
                        lta_turnover, lta_turnover_log, lta_turnover_log_percentile,
                        working_capital_ratio, working_capital_ratio_percentile,
                        ocf_ratio, ocf_ratio_percentile,
                        update_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', all_insert_data)
                conn.commit()
                all_insert_data = []
                
        except Exception as e:
            failed_count += 1
            failed_stocks.append((ts_code, str(e)))
    
    # 提交剩余数据
    if len(all_insert_data) > 0:
        cursor.executemany('''
            INSERT OR REPLACE INTO core_indicators (
                ts_code, end_date,
                ar_turnover, ar_turnover_log, ar_turnover_log_percentile,
                gross_margin, gross_margin_percentile,
                lta_turnover, lta_turnover_log, lta_turnover_log_percentile,
                working_capital_ratio, working_capital_ratio_percentile,
                ocf_ratio, ocf_ratio_percentile,
                update_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', all_insert_data)
        conn.commit()
    
    calc_time = time.time() - start_time
    
    # 总结
    print("\n" + "="*80)
    print("完成！")
    print("="*80)
    print(f"  总耗时: {calc_time/60:.1f} 分钟")
    print(f"  成功: {success_count} 只")
    print(f"  失败: {failed_count} 只")
    print(f"  平均速度: {success_count/(calc_time/60):.1f} 只/分钟")
    
    if failed_count > 0 and failed_count <= 20:
        print(f"\n失败的股票:")
        for ts_code, reason in failed_stocks:
            print(f"  {ts_code}: {reason}")
    elif failed_count > 20:
        print(f"\n失败的股票（前20只）:")
        for ts_code, reason in failed_stocks[:20]:
            print(f"  {ts_code}: {reason}")
    
    print("="*80)
    
    conn.close()

if __name__ == '__main__':
    main()
