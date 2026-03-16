"""
超级优化版：批量重新计算所有股票的核心指标
策略：一次性读取所有数据到内存，批量计算，批量写入
"""
import sqlite3
import pandas as pd
import time
from datetime import datetime
from core_indicators_analyzer import CoreIndicatorsAnalyzer
from tqdm import tqdm

def main():
    print("="*80)
    print("超级优化版：批量重新计算所有股票的核心指标")
    print("="*80)
    
    db_path = 'database/market_data.db'
    conn = sqlite3.connect(db_path)
    
    start_time = time.time()
    
    # 1. 获取所有股票列表（从资产负债表中获取，因为所有股票都有财务数据）
    print("\n步骤1：获取股票列表...")
    stocks_df = pd.read_sql_query('SELECT DISTINCT ts_code FROM balancesheet ORDER BY ts_code', conn)
    all_stocks = stocks_df['ts_code'].tolist()
    print(f"  找到 {len(all_stocks)} 只股票")
    
    # 2. 一次性读取所有财务数据
    print("\n步骤2：批量读取所有财务数据...")
    
    print("  读取资产负债表...")
    balance_all = pd.read_sql_query('SELECT * FROM balancesheet ORDER BY ts_code, end_date', conn)
    print(f"    {len(balance_all)} 条记录")
    
    print("  读取利润表...")
    income_all = pd.read_sql_query('SELECT * FROM income ORDER BY ts_code, end_date', conn)
    print(f"    {len(income_all)} 条记录")
    
    print("  读取现金流量表...")
    cashflow_all = pd.read_sql_query('SELECT * FROM cashflow ORDER BY ts_code, end_date', conn)
    print(f"    {len(cashflow_all)} 条记录")
    
    load_time = time.time() - start_time
    print(f"  数据加载完成，耗时: {load_time:.1f}秒")
    
    # 3. 批量计算指标
    print("\n步骤3：批量计算核心指标...")
    
    analyzer = CoreIndicatorsAnalyzer()
    all_indicators = []
    success_count = 0
    failed_count = 0
    failed_stocks = []
    
    calc_start = time.time()
    
    for ts_code in tqdm(all_stocks, desc="计算进度"):
        try:
            # 筛选当前股票的数据
            balance = balance_all[balance_all['ts_code'] == ts_code].copy()
            income = income_all[income_all['ts_code'] == ts_code].copy()
            cashflow = cashflow_all[cashflow_all['ts_code'] == ts_code].copy()
            
            if len(balance) == 0 or len(income) == 0 or len(cashflow) == 0:
                failed_count += 1
                failed_stocks.append((ts_code, "缺少财务数据"))
                continue
            
            # 计算指标
            indicators = analyzer.calculate_all_indicators(balance, income, cashflow)
            
            if len(indicators) > 0:
                # 添加股票代码
                indicators['ts_code'] = ts_code
                all_indicators.append(indicators)
                success_count += 1
            else:
                failed_count += 1
                failed_stocks.append((ts_code, "计算结果为空"))
                
        except Exception as e:
            failed_count += 1
            failed_stocks.append((ts_code, str(e)))
    
    calc_time = time.time() - calc_start
    print(f"\n  计算完成，耗时: {calc_time/60:.1f}分钟")
    print(f"  成功: {success_count} 只，失败: {failed_count} 只")
    
    # 4. 合并所有指标数据
    print("\n步骤4：合并数据...")
    if len(all_indicators) > 0:
        indicators_df = pd.concat(all_indicators, ignore_index=True)
        print(f"  总计 {len(indicators_df)} 条指标记录")
    else:
        print("  没有计算出任何指标")
        return
    
    # 5. 批量写入数据库
    print("\n步骤5：批量写入数据库...")
    
    write_start = time.time()
    cursor = conn.cursor()
    
    # 清空旧数据
    print("  清空旧数据...")
    cursor.execute('DELETE FROM core_indicators')
    conn.commit()
    
    # 准备批量插入数据
    print("  准备批量插入...")
    insert_data = []
    
    for _, row in indicators_df.iterrows():
        # 获取日期字段（支持中英文）
        end_date = row.get('end_date') or row.get('报告期')
        if isinstance(end_date, str):
            end_date = end_date.replace('-', '')
        
        insert_data.append((
            row['ts_code'],
            str(end_date),
            row.get('ar_turnover_log') or row.get('应收账款周转率对数'),
            row.get('gross_margin') or row.get('毛利率'),
            row.get('lta_turnover_log') or row.get('长期经营资产周转率对数'),
            row.get('working_capital_ratio') or row.get('净营运资本比率'),
            row.get('ocf_ratio') or row.get('经营现金流比率'),
            None,  # ar_turnover_log_percentile 稍后计算
            None,  # gross_margin_percentile
            None,  # lta_turnover_log_percentile
            None,  # working_capital_ratio_percentile
            None,  # ocf_ratio_percentile
            1,  # data_complete
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    # 批量插入
    print(f"  批量插入 {len(insert_data)} 条记录...")
    cursor.executemany('''
        INSERT OR REPLACE INTO core_indicators (
            ts_code, end_date,
            ar_turnover_log, gross_margin, lta_turnover_log,
            working_capital_ratio, ocf_ratio,
            ar_turnover_log_percentile, gross_margin_percentile,
            lta_turnover_log_percentile, working_capital_ratio_percentile,
            ocf_ratio_percentile,
            data_complete, update_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', insert_data)
    
    conn.commit()
    
    write_time = time.time() - write_start
    print(f"  写入完成，耗时: {write_time:.1f}秒")
    
    # 总结
    total_time = time.time() - start_time
    print("\n" + "="*80)
    print("完成！")
    print("="*80)
    print(f"  总耗时: {total_time/60:.1f} 分钟")
    print(f"  数据加载: {load_time:.1f}秒")
    print(f"  指标计算: {calc_time/60:.1f}分钟")
    print(f"  数据写入: {write_time:.1f}秒")
    print(f"  成功: {success_count} 只")
    print(f"  失败: {failed_count} 只")
    
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
