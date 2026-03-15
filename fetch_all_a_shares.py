"""
获取全A股财务数据
"""

import logging
from update_market_data import MarketDataUpdater

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fetch_all_a_shares.log'),
        logging.StreamHandler()
    ]
)

def main():
    """主函数"""
    
    print("="*80)
    print("开始获取全A股财务数据")
    print("="*80)
    
    # 初始化更新器
    updater = MarketDataUpdater(
        config_path='config.yaml',
        db_path='database/market_data.db',
        max_workers=5,  # 5个线程并发
        rate_limit=200  # 每分钟200次调用
    )
    
    # 获取全A股列表（排除北交所，包含ST）
    print("\n1. 获取股票列表...")
    stock_list = updater.get_stock_list(
        exclude_bse=True,  # 排除北交所
        include_st=True    # 包含ST股票
    )
    
    print(f"✓ 找到 {len(stock_list)} 只A股")
    
    # 显示市场分布
    market_dist = stock_list['市场'].value_counts()
    print("\n市场分布:")
    for market, count in market_dist.items():
        print(f"  {market}: {count} 只")
    
    # 询问是否继续
    print("\n" + "="*80)
    print("准备开始获取数据...")
    print(f"总计: {len(stock_list)} 只股票")
    print(f"并发线程: 5")
    print(f"API限流: 200次/分钟")
    print(f"预计耗时: 约 {len(stock_list) * 4 / 200:.1f} 分钟")
    print("="*80)
    
    response = input("\n是否开始获取数据？(y/n): ")
    
    if response.lower() != 'y':
        print("已取消")
        return
    
    # 开始更新数据
    print("\n2. 开始批量更新数据...")
    print("-"*80)
    
    results = updater.update_all_stocks(
        stock_list=stock_list,
        force_update=False  # 增量更新
    )
    
    # 显示结果
    print("\n" + "="*80)
    print("数据更新完成")
    print("="*80)
    print(f"总计: {results['total']} 只股票")
    print(f"成功: {results['success']} 只")
    print(f"失败: {results['failed']} 只")
    print(f"跳过: {results['skipped']} 只")
    print(f"总耗时: {results['duration']:.1f} 分钟")
    print(f"平均速度: {results['speed']:.2f} 只/秒")
    
    # 显示数据库统计
    print("\n数据库统计:")
    stats = updater.db_manager.get_database_stats()
    for table, count in stats.items():
        print(f"  {table}: {count} 条记录")
    
    print("="*80)


if __name__ == '__main__':
    import os
    
    # 创建日志目录
    os.makedirs('logs', exist_ok=True)
    
    main()
