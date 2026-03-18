#!/usr/bin/env python3
"""
历史 TTM 指标回填脚本

功能：
1. 为数据库中所有历史季度生成 TTM 核心指标
2. 支持断点续传
3. 批量处理，自动更新分位数
"""

import argparse
import logging
from update_financial_data import FinancialDataUpdater


def main():
    parser = argparse.ArgumentParser(description='历史 TTM 指标回填脚本')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='配置文件路径')
    parser.add_argument('--db', type=str, default='database/financial_data.db',
                       help='数据库路径')
    parser.add_argument('--workers', type=int, default=5,
                       help='工作线程数（默认5）')
    parser.add_argument('--stocks', type=str, nargs='+',
                       help='指定股票代码列表（可选，不指定则处理所有股票）')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('backfill_ttm_indicators.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("开始回填历史 TTM 指标")
    logger.info("="*60)
    
    # 初始化更新器
    updater = FinancialDataUpdater(
        config_path=args.config,
        db_path=args.db,
        max_workers=args.workers
    )
    
    # 执行 TTM 指标批量计算
    updater.calculate_ttm_indicators_batch(updated_stocks=args.stocks)
    
    logger.info("="*60)
    logger.info("历史 TTM 指标回填完成")
    logger.info("="*60)


if __name__ == '__main__':
    main()
