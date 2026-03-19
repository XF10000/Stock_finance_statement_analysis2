#!/usr/bin/env python3
"""
修复数据库中年报核心指标的 is_ttm 标记错误

问题：年报季度（end_date 以 1231 结尾）的核心指标被错误标记为 is_ttm=1
应该：年报季度应该标记为 is_ttm=0，因为年报本身就是完整年度数据

修复策略：
1. 查找所有 end_date 以 1231 结尾且 is_ttm=1 的记录
2. 将这些记录的 is_ttm 更新为 0
"""

import sqlite3
import sys

def fix_annual_is_ttm(db_path='database/financial_data.db'):
    """修复年报核心指标的 is_ttm 标记"""
    
    print("="*60)
    print("修复年报核心指标的 is_ttm 标记")
    print("="*60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 统计需要修复的记录数
    print("\n1. 检查需要修复的记录...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM core_indicators 
        WHERE end_date LIKE '%1231' AND is_ttm = 1
    """)
    count_to_fix = cursor.fetchone()[0]
    print(f"   发现 {count_to_fix} 条年报记录被错误标记为 is_ttm=1")
    
    if count_to_fix == 0:
        print("\n✓ 没有需要修复的记录")
        conn.close()
        return
    
    # 2. 显示一些示例
    print("\n2. 示例记录（前5条）:")
    cursor.execute("""
        SELECT ts_code, end_date, is_ttm, ar_turnover_log, gross_margin
        FROM core_indicators 
        WHERE end_date LIKE '%1231' AND is_ttm = 1
        LIMIT 5
    """)
    for row in cursor.fetchall():
        ar_val = f"{row[3]:.2f}" if row[3] is not None else "NULL"
        gm_val = f"{row[4]:.2f}" if row[4] is not None else "NULL"
        print(f"   {row[0]} | {row[1]} | is_ttm={row[2]} | ar_turnover={ar_val} | gross_margin={gm_val}")
    
    # 3. 执行修复
    print(f"\n3. 开始修复 {count_to_fix} 条记录...")
    cursor.execute("""
        UPDATE core_indicators 
        SET is_ttm = 0 
        WHERE end_date LIKE '%1231' AND is_ttm = 1
    """)
    
    conn.commit()
    print(f"   ✓ 已将 {cursor.rowcount} 条年报记录的 is_ttm 更新为 0")
    
    # 4. 验证修复结果
    print("\n4. 验证修复结果...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM core_indicators 
        WHERE end_date LIKE '%1231' AND is_ttm = 1
    """)
    remaining = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM core_indicators 
        WHERE end_date LIKE '%1231' AND is_ttm = 0
    """)
    fixed = cursor.fetchone()[0]
    
    print(f"   年报记录 is_ttm=1: {remaining} 条（应该为0）")
    print(f"   年报记录 is_ttm=0: {fixed} 条 ✓")
    
    # 5. 统计各类型记录数
    print("\n5. 最终统计:")
    cursor.execute("""
        SELECT 
            CASE 
                WHEN end_date LIKE '%1231' THEN '年报(1231)'
                ELSE '季报(Q1/Q2/Q3)'
            END as type,
            is_ttm,
            COUNT(*) as count
        FROM core_indicators
        GROUP BY type, is_ttm
        ORDER BY type, is_ttm
    """)
    
    print("   类型          | is_ttm | 记录数")
    print("   " + "-"*40)
    for row in cursor.fetchall():
        print(f"   {row[0]:12} | {row[1]:6} | {row[2]:,}")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✓ 修复完成！")
    print("="*60)

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'database/financial_data.db'
    fix_annual_is_ttm(db_path)
