"""
真正的批量优化版：
1. 一次性从数据库读取所有股票的财务数据（JSON格式）
2. 在内存中解析并批量计算所有指标
3. 批量写回数据库
"""
import sqlite3
import pandas as pd
import json
import time
from datetime import datetime
from core_indicators_analyzer import CoreIndicatorsAnalyzer
from tqdm import tqdm

def parse_financial_data(data_rows):
    """解析JSON格式的财务数据"""
    if len(data_rows) == 0:
        return pd.DataFrame()
    
    records = []
    for row in data_rows:
        ts_code, end_date, data_json = row
        if data_json:
            data_list = json.loads(data_json)
            # JSON中存储的是列表，通常只有一条记录
            if isinstance(data_list, list) and len(data_list) > 0:
                data = data_list[0]
                data['ts_code'] = ts_code
                data['报告期'] = int(end_date)
                records.append(data)
    
    return pd.DataFrame(records) if records else pd.DataFrame()

def main():
    print("="*80)
    print("批量优化版：一次性读取所有数据，内存计算，批量写入")
    print("="*80)
    
    db_path = 'database/market_data.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    start_time = time.time()
    
    # 1. 获取所有股票列表
    print("\n步骤1：获取股票列表...")
    cursor.execute('SELECT DISTINCT ts_code FROM balancesheet ORDER BY ts_code')
    all_stocks = [row[0] for row in cursor.fetchall()]
    print(f"  找到 {len(all_stocks)} 只股票")
    
    # 2. 一次性读取所有财务数据（JSON格式）
    print("\n步骤2：批量读取所有财务数据...")
    
    print("  读取资产负债表...")
    cursor.execute('SELECT ts_code, end_date, data_json FROM balancesheet')
    balance_rows = cursor.fetchall()
    print(f"    {len(balance_rows)} 条记录")
    
    print("  读取利润表...")
    cursor.execute('SELECT ts_code, end_date, data_json FROM income')
    income_rows = cursor.fetchall()
    print(f"    {len(income_rows)} 条记录")
    
    print("  读取现金流量表...")
    cursor.execute('SELECT ts_code, end_date, data_json FROM cashflow')
    cashflow_rows = cursor.fetchall()
    print(f"    {len(cashflow_rows)} 条记录")
    
    load_time = time.time() - start_time
    print(f"  数据读取完成，耗时: {load_time:.1f}秒")
    
    # 3. 解析JSON数据
    print("\n步骤3：解析JSON数据...")
    parse_start = time.time()
    
    print("  解析资产负债表...")
    balance_all = parse_financial_data(balance_rows)
    print(f"    {len(balance_all)} 条记录")
    
    print("  解析利润表...")
    income_all = parse_financial_data(income_rows)
    print(f"    {len(income_all)} 条记录")
    
    print("  解析现金流量表...")
    cashflow_all = parse_financial_data(cashflow_rows)
    print(f"    {len(cashflow_all)} 条记录")
    
    parse_time = time.time() - parse_start
    print(f"  解析完成，耗时: {parse_time:.1f}秒")
    
    # 4. 批量计算指标
    print("\n步骤4：批量计算核心指标...")
    
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
    
    # 5. 合并所有指标数据
    print("\n步骤5：合并数据...")
    if len(all_indicators) > 0:
        indicators_df = pd.concat(all_indicators, ignore_index=True)
        print(f"  总计 {len(indicators_df)} 条指标记录")
    else:
        print("  没有计算出任何指标")
        return
    
    # 6. 批量写入数据库
    print("\n步骤6：批量写入数据库...")
    
    write_start = time.time()
    
    # 清空旧数据
    print("  清空旧数据...")
    cursor.execute('DELETE FROM core_indicators')
    conn.commit()
    
    # 准备批量插入数据
    print("  准备批量插入...")
    insert_data = []
    
    for _, row in indicators_df.iterrows():
        insert_data.append((
            row['ts_code'],
            int(row['报告期']),
            row.get('应收账款周转率对数'),
            None,  # percentile稍后计算
            row.get('毛利率'),
            None,
            row.get('长期经营资产周转率对数'),
            None,
            row.get('净营运资本比率'),
            None,
            row.get('经营现金流比率'),
            None,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    # 批量插入
    print(f"  批量插入 {len(insert_data)} 条记录...")
    cursor.executemany('''
        INSERT INTO core_indicators (
            ts_code, end_date,
            ar_turnover_log, ar_turnover_log_percentile,
            gross_margin, gross_margin_percentile,
            lta_turnover_log, lta_turnover_log_percentile,
            working_capital_ratio, working_capital_ratio_percentile,
            ocf_ratio, ocf_ratio_percentile,
            update_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    print(f"  数据读取: {load_time:.1f}秒")
    print(f"  JSON解析: {parse_time:.1f}秒")
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
