"""
快速测试脚本：验证 Tushare 连接和配置
"""

import sys
from tushare_client import TushareClient


def test_connection():
    """测试 Tushare API 连接"""
    print("="*60)
    print("Tushare API 连接测试")
    print("="*60)
    
    try:
        # 初始化客户端
        print("\n1. 初始化客户端...")
        client = TushareClient(config_path='config.yaml')
        print("   ✓ 客户端初始化成功")
        
        # 测试获取股票基本信息
        print("\n2. 测试获取股票基本信息...")
        ts_code = '000001.SZ'  # 平安银行
        list_date = client.get_stock_list_date(ts_code)
        if list_date:
            print(f"   ✓ 成功获取 {ts_code} 上市日期: {list_date}")
        else:
            print(f"   ✗ 无法获取 {ts_code} 上市日期")
            return False
        
        # 测试获取小量数据
        print("\n3. 测试获取财务数据（最近1年）...")
        data = client.get_all_financial_data(
            ts_code=ts_code,
            start_date='20230101',
            end_date='20231231'
        )
        
        # 检查数据
        success = True
        for name, df in data.items():
            if df is not None and len(df) > 0:
                print(f"   ✓ {name}: {len(df)} 条记录")
            else:
                print(f"   ✗ {name}: 无数据")
                success = False
        
        if success:
            print("\n" + "="*60)
            print("✓ 所有测试通过！系统运行正常")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("✗ 部分测试失败，请检查配置或网络连接")
            print("="*60)
            return False
            
    except FileNotFoundError as e:
        print(f"\n✗ 配置文件错误: {e}")
        print("   请确保 config.yaml 文件存在且格式正确")
        return False
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        print("   可能原因：")
        print("   1. Tushare Token 无效")
        print("   2. 网络连接问题")
        print("   3. Tushare 积分不足")
        return False


if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)
