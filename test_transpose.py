"""
测试转置功能
"""
from tushare_client import TushareClient

# 初始化客户端
client = TushareClient()

# 获取测试数据
ts_code = '000001.SZ'
print(f"获取 {ts_code} 的财务数据...")

data = client.get_all_financial_data(ts_code, start_date='20240101', end_date='20241231')

# 测试转置
print("\n原始数据格式（字段在列）：")
print(data['fina_indicator'].head())

print("\n转置后数据格式（字段在行）：")
df_transposed = client.transpose_data(data['fina_indicator'])
print(df_transposed.head(20))

# 保存为转置格式
print("\n保存转置格式的 CSV 文件...")
client.save_to_csv(data, ts_code, output_dir='./data/test', transpose=True)

print("\n测试完成！")
