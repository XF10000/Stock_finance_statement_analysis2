#!/usr/bin/env python3
"""
批量更新文档中的命名引用
"""
import os
import re

# 定义替换规则
replacements = [
    ('market_data_manager.py', 'financial_data_manager.py'),
    ('market_analyzer.py', 'financial_data_analyzer.py'),
    ('update_market_data.py', 'update_financial_data.py'),
    ('update_market_data.log', 'update_financial_data.log'),
    ('MarketDataManager', 'FinancialDataManager'),
    ('MarketAnalyzer', 'FinancialDataAnalyzer'),
    ('MarketDataUpdater', 'FinancialDataUpdater'),
    ('market_data.db', 'financial_data.db'),
    ('市场数据管理器', '财务数据管理器'),
    ('市场数据更新', '财务数据更新'),
    ('市场数据数据库', '财务数据数据库'),
]

# 需要更新的文档文件
doc_files = [
    'README.md',
    'docs/USER_GUIDE.md',
    '数据库更新说明.md',
    'docs/PROJECT_STRUCTURE.md',
    'docs/四大核心财务指标分析_开发计划.md',
    'PROJECT_ANALYSIS_SUMMARY.md',
    'REDUNDANT_FILES.md',
]

def update_file(filepath):
    """更新单个文件"""
    if not os.path.exists(filepath):
        print(f"⚠️  文件不存在: {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 应用所有替换规则
        for old, new in replacements:
            content = content.replace(old, new)
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 已更新: {filepath}")
            return True
        else:
            print(f"  无需更新: {filepath}")
            return False
    
    except Exception as e:
        print(f"✗ 更新失败 {filepath}: {e}")
        return False

def main():
    print("="*60)
    print("批量更新文档中的命名引用")
    print("="*60)
    
    updated_count = 0
    
    for doc_file in doc_files:
        if update_file(doc_file):
            updated_count += 1
    
    print("\n" + "="*60)
    print(f"完成！共更新 {updated_count} 个文件")
    print("="*60)

if __name__ == '__main__':
    main()
