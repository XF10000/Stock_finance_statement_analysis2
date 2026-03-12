"""
主程序：从 Tushare 获取公司财务数据
"""

import argparse
from datetime import datetime
from tushare_client import TushareClient


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='从 Tushare 获取公司财务数据')
    parser.add_argument('ts_code', type=str, help='股票代码（例如：000001.SZ）')
    parser.add_argument('--start-date', type=str, help='开始日期（YYYYMMDD）')
    parser.add_argument('--end-date', type=str, help='结束日期（YYYYMMDD）')
    parser.add_argument('--output-dir', type=str, default='./data', help='数据输出目录')
    parser.add_argument('--format', type=str, choices=['csv', 'excel', 'both'], 
                       default='csv', help='输出格式（csv/excel/both）')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    
    args = parser.parse_args()
    
    # 初始化客户端
    print(f"初始化 Tushare 客户端...")
    client = TushareClient(config_path=args.config)
    
    # 获取财务数据
    print(f"\n开始获取 {args.ts_code} 的财务数据...")
    if args.start_date:
        print(f"日期范围: {args.start_date} 至 {args.end_date or '至今'}")
    else:
        print(f"获取全部历史数据...")
    
    data = client.get_all_financial_data(
        ts_code=args.ts_code,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # 保存数据
    print(f"\n保存数据到: {args.output_dir}")
    if args.format in ['csv', 'both']:
        client.save_to_csv(data, args.ts_code, args.output_dir)
    
    if args.format in ['excel', 'both']:
        client.save_to_excel(data, args.ts_code, args.output_dir)
    
    # 显示数据摘要
    print("\n" + "="*60)
    print("数据摘要:")
    print("="*60)
    for name, df in data.items():
        if df is not None and len(df) > 0:
            print(f"{name:20s}: {len(df):6d} 条记录, {len(df.columns)} 个字段")
            if len(df) > 0:
                print(f"  日期范围: {df['end_date'].min()} 至 {df['end_date'].max()}")
        else:
            print(f"{name:20s}: 无数据")
    print("="*60)
    
    print(f"\n完成！数据已保存到 {args.output_dir}")


if __name__ == '__main__':
    main()
