"""
优化版：批量重新计算所有报告期的市场分布和分位数排名
"""
import pandas as pd
import numpy as np
from market_data_manager import MarketDataManager
from datetime import datetime
import time

def calculate_percentile_rank(value, all_values):
    """计算某个值在所有值中的分位数排名（0-100）"""
    if pd.isna(value):
        return None
    valid_values = all_values.dropna()
    if len(valid_values) == 0:
        return None
    # 计算有多少个值小于等于当前值
    rank = (valid_values <= value).sum() / len(valid_values) * 100
    return rank

def process_single_period(conn, end_date, exclude_outliers=True, outlier_std=3.0):
    """
    处理单个报告期的市场分布和分位数排名
    
    Args:
        conn: 数据库连接
        end_date: 报告期
        exclude_outliers: 是否排除异常值
        outlier_std: 异常值标准差倍数
    """
    # 1. 读取该报告期所有股票的指标数据
    query = '''
        SELECT ts_code, ar_turnover_log, gross_margin, lta_turnover_log,
               working_capital_ratio, ocf_ratio
        FROM core_indicators
        WHERE end_date = ?
    '''
    df = pd.read_sql_query(query, conn, params=(end_date,))
    
    if len(df) == 0:
        print(f"  {end_date}: 无数据")
        return 0
    
    indicator_columns = {
        'ar_turnover_log': '应收账款周转率对数',
        'gross_margin': '毛利率',
        'lta_turnover_log': '长期经营资产周转率对数',
        'working_capital_ratio': '净营运资本比率',
        'ocf_ratio': '经营现金流比率'
    }
    
    # 2. 计算市场分布并保存
    cursor = conn.cursor()
    
    for col_name, cn_name in indicator_columns.items():
        if col_name not in df.columns:
            continue
        
        # 获取有效数据
        data = df[col_name].dropna()
        
        if len(data) == 0:
            continue
        
        # 处理异常值
        if exclude_outliers and len(data) > 10:
            mean = data.mean()
            std = data.std()
            lower_bound = mean - outlier_std * std
            upper_bound = mean + outlier_std * std
            data = data[(data >= lower_bound) & (data <= upper_bound)]
        
        # 计算统计指标
        stats = {
            'count': len(data),
            'mean': float(data.mean()),
            'std': float(data.std()),
            'min': float(data.min()),
            'p25': float(data.quantile(0.25)),
            'p50': float(data.quantile(0.50)),
            'p75': float(data.quantile(0.75)),
            'max': float(data.max())
        }
        
        # 保存市场分布
        cursor.execute('''
            INSERT OR REPLACE INTO market_distribution
            (end_date, indicator_name, count, mean, median, std, min, p25, p75, max, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            end_date, col_name, stats['count'], stats['mean'], stats['p50'],
            stats['std'], stats['min'], stats['p25'], stats['p75'], stats['max'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    # 3. 批量计算所有股票的分位数排名
    update_data = []
    
    for _, row in df.iterrows():
        ts_code = row['ts_code']
        percentiles = {}
        
        for col_name in indicator_columns.keys():
            if col_name in df.columns and pd.notna(row[col_name]):
                percentile = calculate_percentile_rank(row[col_name], df[col_name])
                percentiles[f'{col_name}_percentile'] = percentile
            else:
                percentiles[f'{col_name}_percentile'] = None
        
        update_data.append((
            percentiles.get('ar_turnover_log_percentile'),
            percentiles.get('gross_margin_percentile'),
            percentiles.get('lta_turnover_log_percentile'),
            percentiles.get('working_capital_ratio_percentile'),
            percentiles.get('ocf_ratio_percentile'),
            ts_code,
            end_date
        ))
    
    # 4. 批量更新分位数排名
    cursor.executemany('''
        UPDATE core_indicators
        SET ar_turnover_log_percentile = ?,
            gross_margin_percentile = ?,
            lta_turnover_log_percentile = ?,
            working_capital_ratio_percentile = ?,
            ocf_ratio_percentile = ?
        WHERE ts_code = ? AND end_date = ?
    ''', update_data)
    
    conn.commit()
    
    return len(df)

def main():
    print("="*80)
    print("优化版：批量重新计算所有报告期的市场分布")
    print("="*80)
    
    db = MarketDataManager('database/market_data.db')
    conn = db.get_connection()
    
    # 获取所有报告期
    query = 'SELECT DISTINCT end_date FROM core_indicators ORDER BY end_date'
    periods = pd.read_sql_query(query, conn)['end_date'].tolist()
    
    print(f"\n找到 {len(periods)} 个报告期")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    start_time = time.time()
    processed = 0
    
    for i, period in enumerate(periods, 1):
        period_start = time.time()
        
        count = process_single_period(conn, period)
        
        period_elapsed = time.time() - period_start
        total_elapsed = time.time() - start_time
        
        if count > 0:
            processed += 1
            avg_time = total_elapsed / processed
            remaining = (len(periods) - i) * avg_time
            
            print(f"  [{i}/{len(periods)}] {period}: {count}只股票 "
                  f"({period_elapsed:.1f}秒, 预计剩余: {remaining/60:.1f}分钟)")
    
    total_time = time.time() - start_time
    
    print("\n" + "="*80)
    print("完成！")
    print("="*80)
    print(f"  处理报告期: {processed}/{len(periods)}")
    print(f"  总耗时: {total_time/60:.1f} 分钟")
    print(f"  平均速度: {processed/total_time:.2f} 个报告期/秒")
    print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    conn.close()

if __name__ == '__main__':
    main()
