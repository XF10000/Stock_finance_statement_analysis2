"""
主程序：从 Tushare 获取公司财务数据
"""

import argparse
from datetime import datetime
from tushare_client import TushareClient


def normalize_stock_code(ts_code: str) -> str:
    """
    规范化股票代码，自动补全交易所后缀
    
    Args:
        ts_code: 股票代码（可以是纯数字或带后缀）
        
    Returns:
        规范化后的股票代码（带交易所后缀）
    
    Examples:
        '000333' -> '000333.SZ'
        '600519' -> '600519.SH'
        '000001.SZ' -> '000001.SZ'
    """
    # 如果已经有后缀，直接返回
    if '.' in ts_code:
        return ts_code.upper()
    
    # 补全代码到6位数字
    code = ts_code.zfill(6)
    
    # 根据代码开头判断交易所
    # 深圳：000、002、003、300开头
    # 上海：600、601、603、605、688开头
    if code.startswith(('000', '002', '003', '300')):
        return f"{code}.SZ"
    elif code.startswith(('600', '601', '603', '605', '688')):
        return f"{code}.SH"
    else:
        # 默认深圳（兼容其他代码）
        return f"{code}.SZ"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='从 Tushare 获取公司财务数据')
    parser.add_argument('ts_code', type=str, help='股票代码（例如：000333 或 600519.SH）')
    parser.add_argument('--start-date', type=str, help='开始日期（YYYYMMDD）')
    parser.add_argument('--end-date', type=str, help='结束日期（YYYYMMDD）')
    parser.add_argument('--output-dir', type=str, default='./data', help='数据输出目录')
    parser.add_argument('--format', type=str, choices=['csv', 'excel', 'both'], 
                       default='csv', help='输出格式（csv/excel/both）')
    parser.add_argument('--no-transpose', action='store_true', 
                       help='不转置数据（使用原始格式：字段横向，时间纵向）')
    parser.add_argument('--no-translate', action='store_true', help='不翻译字段名（使用英文列名）')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    
    args = parser.parse_args()
    
    # 规范化股票代码（自动补全交易所后缀）
    ts_code = normalize_stock_code(args.ts_code)
    
    # 初始化客户端
    print(f"初始化 Tushare 客户端...")
    client = TushareClient(config_path=args.config)
    
    # 获取财务数据
    print(f"\n开始获取 {ts_code} 的财务数据...")
    if args.start_date:
        print(f"日期范围: {args.start_date} 至 {args.end_date or '至今'}")
    else:
        print(f"获取全部历史数据...")
    
    # 默认翻译为中文
    translate = not args.no_translate
    if translate:
        print(f"字段名翻译: 中文（默认）")
    else:
        print(f"字段名翻译: 英文")
    
    # 默认转置数据格式
    transpose = not args.no_transpose
    if transpose:
        print(f"数据格式: 转置（字段纵向，时间横向）- 便于分析")
    else:
        print(f"数据格式: 原始（字段横向，时间纵向）")
    
    data = client.get_all_financial_data(
        ts_code=ts_code,
        start_date=args.start_date,
        end_date=args.end_date,
        translate=translate
    )
    
    # 保存数据
    print(f"\n保存数据到: {args.output_dir}")
    if args.format in ['csv', 'both']:
        client.save_to_csv(data, ts_code, args.output_dir, transpose=transpose)
    
    if args.format in ['excel', 'both']:
        client.save_to_excel(data, ts_code, args.output_dir, transpose=transpose)
    
    # 显示数据摘要
    print("\n" + "="*60)
    print("数据摘要:")
    print("="*60)
    for name, df in data.items():
        if df is not None and len(df) > 0:
            print(f"{name:20s}: {len(df):6d} 条记录, {len(df.columns)} 个字段")
            if len(df) > 0:
                # 根据是否翻译选择列名
                date_col = '报告期' if '报告期' in df.columns else 'end_date'
                print(f"  日期范围: {df[date_col].min()} 至 {df[date_col].max()}")
        else:
            print(f"{name:20s}: 无数据")
    print("="*60)
    
    print(f"\n完成！数据已保存到 {args.output_dir}")


if __name__ == '__main__':
    main()
