"""
安全获取全A股财务数据（单线程 + 断点续传）
"""

import logging
import os
from datetime import datetime
from update_market_data import MarketDataUpdater

# 配置日志
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/fetch_all_a_shares_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# 断点续传状态文件
PROGRESS_FILE = 'logs/fetch_progress.txt'


def save_progress(ts_code: str, success: bool):
    """保存进度"""
    with open(PROGRESS_FILE, 'a') as f:
        status = 'SUCCESS' if success else 'FAILED'
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|{ts_code}|{status}\n")


def get_last_completed():
    """获取最后完成的股票代码"""
    if not os.path.exists(PROGRESS_FILE):
        return None
    
    with open(PROGRESS_FILE, 'r') as f:
        lines = f.readlines()
    
    if not lines:
        return None
    
    # 找到最后一个成功的记录
    for line in reversed(lines):
        parts = line.strip().split('|')
        if len(parts) == 3 and parts[2] == 'SUCCESS':
            return parts[1]
    
    return None


def main():
    """主函数"""
    
    print("="*80)
    print("安全获取全A股财务数据（单线程 + 断点续传）")
    print("="*80)
    
    # 初始化更新器（单线程）
    updater = MarketDataUpdater(
        config_path='config.yaml',
        db_path='database/market_data.db',
        max_workers=1  # 单线程
    )
    
    # 获取全A股列表
    print("\n1. 获取股票列表...")
    all_stocks = updater.get_all_a_stocks(exclude_bse=True)
    print(f"✓ 找到 {len(all_stocks)} 只A股")
    
    # 检查断点续传
    last_completed = get_last_completed()
    
    if last_completed:
        print(f"\n检测到断点续传记录")
        print(f"最后完成: {last_completed}")
        
        # 找到断点位置
        resume_index = next((i for i, s in enumerate(all_stocks) if s['ts_code'] == last_completed), -1)
        
        if resume_index >= 0:
            # 从下一只股票开始
            all_stocks = all_stocks[resume_index + 1:]
            print(f"将从第 {resume_index + 2} 只股票继续")
            print(f"剩余: {len(all_stocks)} 只股票")
        else:
            print(f"未找到断点位置，将从头开始")
    
    if len(all_stocks) == 0:
        print("\n所有股票已完成！")
        return
    
    # 显示配置信息
    print("\n2. 配置信息")
    print("-"*80)
    print(f"总计: {len(all_stocks)} 只股票")
    print(f"并发线程: 1（单线程）")
    print(f"API限流: 180次/分钟（安全配置）")
    print(f"请求间隔: 0.3秒")
    print(f"预计耗时: 约 {len(all_stocks) * 2.0 / 60:.1f} 分钟 ({len(all_stocks) * 2.0 / 3600:.1f} 小时)")
    print(f"断点续传: 已启用")
    print(f"进度文件: {PROGRESS_FILE}")
    print("-"*80)
    
    # 开始执行
    print("\n准备开始获取数据...")
    
    # 开始更新数据
    print("\n3. 开始批量更新数据...")
    print("-"*80)
    
    success_count = 0
    failed_count = 0
    start_time = datetime.now()
    
    for i, stock in enumerate(all_stocks, 1):
        ts_code = stock['ts_code']
        
        try:
            # 获取数据
            success = updater.fetch_stock_all_data(ts_code, force_update=False)
            
            # 保存进度
            save_progress(ts_code, success)
            
            if success:
                success_count += 1
            else:
                failed_count += 1
            
            # 每10只显示一次进度
            if i % 10 == 0 or i == len(all_stocks):
                elapsed = (datetime.now() - start_time).total_seconds()
                speed = i / elapsed if elapsed > 0 else 0
                eta = (len(all_stocks) - i) / speed if speed > 0 else 0
                
                print(f"进度: {i}/{len(all_stocks)} ({i/len(all_stocks)*100:.1f}%) | "
                      f"成功: {success_count} | 失败: {failed_count} | "
                      f"速度: {speed:.2f} 只/秒 | 预计剩余: {eta/60:.1f} 分钟")
        
        except KeyboardInterrupt:
            print("\n\n用户中断！")
            print(f"已完成: {i}/{len(all_stocks)} 只股票")
            print(f"成功: {success_count} 只")
            print(f"失败: {failed_count} 只")
            print(f"\n可以使用断点续传继续：")
            print(f"  python3 fetch_all_a_shares_safe.py")
            return
        
        except Exception as e:
            logging.error(f"处理 {ts_code} 时发生异常: {e}")
            save_progress(ts_code, False)
            failed_count += 1
            continue
    
    # 显示最终结果
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "="*80)
    print("数据更新完成")
    print("="*80)
    print(f"总计: {len(all_stocks)} 只股票")
    print(f"成功: {success_count} 只")
    print(f"失败: {failed_count} 只")
    print(f"总耗时: {elapsed/60:.1f} 分钟 ({elapsed/3600:.2f} 小时)")
    print(f"平均速度: {len(all_stocks)/elapsed:.2f} 只/秒")
    
    # 显示数据库统计
    print("\n数据库统计:")
    stats = updater.db_manager.get_database_stats()
    for table, count in stats.items():
        print(f"  {table}: {count:,} 条记录")
    
    print("="*80)


if __name__ == '__main__':
    main()
