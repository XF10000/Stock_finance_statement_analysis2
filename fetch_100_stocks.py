"""
测试获取100家公司的财务数据
"""

import logging
from update_market_data import MarketDataUpdater

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """主函数"""
    
    print("="*80)
    print("测试获取100家公司的财务数据")
    print("="*80)
    
    # 初始化更新器
    updater = MarketDataUpdater(
        config_path='config.yaml',
        db_path='database/market_data.db',
        max_workers=5  # 5个线程并发
    )
    
    # 获取全A股列表
    print("\n1. 获取股票列表...")
    all_stocks = updater.get_all_a_stocks(exclude_bse=True)
    
    print(f"✓ 找到 {len(all_stocks)} 只A股")
    
    # 只取前100家
    stocks_100 = all_stocks[:100]
    
    print(f"\n选取前100家公司进行测试")
    print(f"股票代码范围: {stocks_100[0]['ts_code']} 至 {stocks_100[-1]['ts_code']}")
    
    # 开始更新数据
    print("\n2. 开始批量更新数据...")
    print("-"*80)
    print(f"总计: {len(stocks_100)} 只股票")
    print(f"并发线程: 5")
    print(f"API限流: 200次/分钟")
    print(f"预计耗时: 约 {len(stocks_100) * 4 / 200:.1f} 分钟")
    print("-"*80)
    
    results = updater.update_all_stocks(
        stocks=stocks_100,
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
    
    # 显示失败的股票
    if results['failed'] > 0:
        print("\n失败的股票:")
        failed_stocks = [code for code, success in results.get('details', {}).items() if not success]
        for code in failed_stocks[:10]:
            print(f"  {code}")
        if len(failed_stocks) > 10:
            print(f"  ... 还有 {len(failed_stocks)-10} 只")


if __name__ == '__main__':
    main()
