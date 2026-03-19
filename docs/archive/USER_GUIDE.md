# 用户使用指南

## 目录

1. [快速开始](#快速开始)
2. [数据采集详解](#数据采集详解)
3. [数据分析详解](#数据分析详解)
4. [常见使用场景](#常见使用场景)
5. [高级功能](#高级功能)
6. [故障排查](#故障排查)

---

## 快速开始

### 第一次使用

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 Tushare Token
cp config.yaml.example config.yaml
# 编辑 config.yaml，填入你的 Token

# 3. 初始化数据库（采集所有A股数据）
python update_financial_data.py --init  # 完成后自动计算年报+TTM核心指标

# 4. 分析任意股票
python main.py 000333
```

### 日常使用

```bash
# 每季度更新一次数据
python update_financial_data.py --update-latest  # tqdm 进度 + 自动计算核心指标

# 随时分析任意股票（无需 API）
python main.py 603345
python main.py 600900
```

---

## 数据采集详解

### 1. 全量初始化

**命令**:
```bash
python update_financial_data.py --init  # 自动计算核心指标
```

**说明**:
- 采集所有A股的全部历史财务数据
- 包括：财务四表 + 总股本 + 分红数据
- 首次运行时间较长（取决于股票数量和 API 积分）
- 自动创建数据库：`database/financial_data.db`

**参数**:
```bash
# 指定线程数（默认4，建议不超过8）
python update_financial_data.py --init --max-workers 8

# 断点续传（从某只股票继续）
python update_financial_data.py --init --resume-from 000333.SZ

# 指定数据库路径
python update_financial_data.py --init --db-path /path/to/db
```

**进度显示**:
```
============================================================
批量更新所有股票数据
============================================================
总股票数: 5000
已完成: 100/5000 (2.0%)
成功: 95, 失败: 5, 跳过: 0
预计剩余时间: 2.5 小时
```

**注意事项**:
- 需要足够的 Tushare API 积分
- 建议在非高峰期运行
- 支持中断后继续（使用 --resume-from）
- 失败的股票会记录在日志中

### 2. 增量更新

**命令**:
```bash
python update_financial_data.py --update-latest
```

**说明**:
- 只更新最新季度的数据
- 自动判断应更新的季度（默认）
- 只获取缺失数据，避免重复请求
- 如需补齐总股本/分红数据，请运行 `--update-dividend-totalshares`
- 建议每季度财报更新后执行
- 1-4月：更新去年Q4（12月31日）
- 5-8月：更新今年Q1（3月31日）
- 9-10月：更新今年Q2（6月30日）
- 11-12月：更新今年Q3（9月30日）

### 3. 重新计算指标

**命令**:
```bash
python update_financial_data.py --recalculate-all
```

**说明**:
- 清空并重新计算所有核心指标
- 涉及大量计算和写入，耗时较长
- 适合数据库发生重大变动时使用
- `--init` 已自动执行年报+TTM 指标计算，通常无需再运行本命令

### 4. 补齐总股本 & 分红数据（可选）

**命令**:
```bash
python update_financial_data.py --update-dividend-totalshares
```

**说明**:
- 智能扫描所有股票，仅为缺失的报告期调用 API
- 与其他命令一样自带 tqdm 进度条，可查看“总股本/分红”补齐数量
- 适合历史数据库或增量更新后补充缺口
- 首次运行时间较长（取决于股票数量和 API 积分）
- 自动创建数据库：`database/financial_data.db`

**参数**:
```bash
# 指定线程数（默认4，建议不超过8）
python update_financial_data.py --update-dividend-totalshares --max-workers 8

# 断点续传（从某只股票继续）
python update_financial_data.py --update-dividend-totalshares --resume-from 000333.SZ

# 指定数据库路径
python update_financial_data.py --update-dividend-totalshares --db-path /path/to/db
```

**进度显示**:
```
数据采集进度: 45%|████████▌         | 2250/5000 [15:30<17:20, 2.64只/s, 成功=2100, 失败=50, 跳过=100]
```

新的 tqdm 进度条会实时刷新成功/失败/跳过数量并给出预计剩余时间。

**注意事项**:
- 需要足够的 Tushare API 积分
- 建议在非高峰期运行
- 支持中断后继续（使用 --resume-from）
- 失败的股票会记录在日志中

---

## 数据分析详解

### 1. 基本分析

**命令**:
```bash
python main.py 000333
```

**自动生成**:
1. 通过 API 获取所有数据
2. 写入数据库（支持断点续传 + 批量写入线程）
3. tqdm 进度条实时显示“成功/失败/跳过”统计

**输出文件**:
```
data/
├── 000333.SZ_balancesheet_restructured.csv
├── 000333.SZ_income_restructured.csv
├── 000333.SZ_cashflow_restructured.csv
├── 000333.SZ_balance_sheet_annual_ttm.csv
├── 000333.SZ_income_statement_annual_ttm.csv
├── 000333.SZ_cashflow_statement_annual_ttm.csv
└── 000333.SZ_financial_report.html
```

### 2. 日期范围筛选

**命令**:
```bash
python main.py 000333 --start-date 20200101 --end-date 20231231
```

**说明**:
- 只分析指定日期范围内的数据
- 日期格式：YYYYMMDD
- 适合专注于特定时期的分析

### 3. 输出格式控制

**CSV 格式**（默认）:
```bash
python main.py 000333 --format csv
```

**Excel 格式**:
```bash
python main.py 000333 --format excel
```

**同时输出**:
```bash
python main.py 000333 --format both
```

### 4. 分红数据导出

**命令**:
```bash
python main.py 000333 --save-dividend-excel
```

**输出**:
- `000333.SZ_分红送股.xlsx`
- 包含完整的分红送股记录

### 5. 年报年数控制

**默认**（所有历史年份）:
```bash
python main.py 000333
```

**指定年数**:
```bash
python main.py 000333 --years 10
```

**不生成年报+TTM**:
```bash
python main.py 000333 --no-annual-ttm
```

---

## 常见使用场景

### 场景 1: 首次建立数据库

```bash
# 1. 配置 Token
cp config.yaml.example config.yaml
vim config.yaml  # 填入 Token

# 2. 初始化数据库
python update_financial_data.py --init --max-workers 4

# 3. 等待完成（可能需要几小时）
# 4. 分析股票
python main.py 000333
```

### 场景 2: 定期数据更新

```bash
# 每季度财报发布后运行
python update_financial_data.py --update-latest  # tqdm 进度 + 自动计算核心指标

# 更新完成后分析
python main.py 000333
```

### 场景 3: 批量分析多只股票

```bash
# 创建股票列表
cat > stocks.txt << EOF
000333
603345
600900
EOF

# 批量分析
while read stock; do
    python main.py $stock --output-dir ./reports/$stock
done < stocks.txt
```

### 场景 4: 特定时期分析

```bash
# 分析2020-2023年的数据
python main.py 000333 \
    --start-date 20200101 \
    --end-date 20231231 \
    --output-dir ./analysis_2020_2023
```

### 场景 5: 数据采集中断恢复

```bash
# 假设在 000500.SZ 处中断
python update_financial_data.py --init --resume-from 000500.SZ
```

---

## 高级功能

### 1. Python API 使用

**数据采集**:
```python
from update_financial_data import FinancialDataUpdater

updater = FinancialDataUpdater(
    config_path='config.yaml',
    db_path='database/financial_data.db',
    max_workers=4
)

# 获取单只股票
success = updater.fetch_stock_all_data('000333.SZ', force_update=True)

# 批量更新
stocks = updater.get_stock_list()
updater.update_all_stocks(stocks, force_update=False)
```

**数据访问**:
```python
from financial_data_manager import FinancialDataManager

db = FinancialDataManager('database/financial_data.db')

# 读取财务数据
balance_df = db.get_financial_data('000333.SZ', 'balancesheet')
income_df = db.get_financial_data('000333.SZ', 'income')

# 读取总股本
total_share_df = db.get_total_share_data('000333.SZ')

# 读取分红数据
dividend_df = db.get_dividend_data('000333.SZ')

# 日期范围筛选
data = db.get_financial_data(
    '000333.SZ', 
    'balancesheet',
    start_date='20200101',
    end_date='20231231'
)

# 检查数据是否存在
exists = db.check_data_exists('000333.SZ', '20231231', 'balancesheet')

# 数据库统计
stats = db.get_database_stats()
print(stats)
```

### 2. 自定义报表重构

```python
from balance_sheet_restructure import restructure_balance_sheet
from income_statement_restructure import restructure_income_statement
import pandas as pd

# 读取数据
db = FinancialDataManager('database/financial_data.db')
balance_df = db.get_financial_data('000333.SZ', 'balancesheet')

# 转置数据
def transpose_data(df):
    date_col = '报告期' if '报告期' in df.columns else 'end_date'
    df_copy = df.copy().set_index(date_col)
    df_transposed = df_copy.T.reset_index()
    df_transposed = df_transposed.rename(columns={'index': '项目'})
    return df_transposed

df_transposed = transpose_data(balance_df)

# 重构
df_restructured = restructure_balance_sheet(df_transposed)

# 保存
df_restructured.to_csv('custom_balance.csv', index=False)
```

### 3. 数据库直接查询

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('database/financial_data.db')

# 查询所有股票列表
stocks = pd.read_sql("SELECT * FROM stock_list", conn)

# 查询特定股票的总股本
query = """
SELECT end_date, total_share 
FROM total_share 
WHERE ts_code = '000333.SZ'
ORDER BY end_date DESC
"""
total_share = pd.read_sql(query, conn)

# 查询分红数据
query = """
SELECT end_date, cash_div, stk_div 
FROM dividend 
WHERE ts_code = '000333.SZ'
ORDER BY end_date DESC
"""
dividend = pd.read_sql(query, conn)

conn.close()
```

---

## 故障排查

### 问题 1: Token 错误

**错误信息**:
```
抱歉，您每分钟最多访问该接口200次
```

**解决方案**:
1. 检查 config.yaml 中的 token 是否正确
2. 减少 --max-workers 线程数
3. 等待一分钟后重试

### 问题 2: 积分不足

**错误信息**:
```
抱歉，您没有访问该接口的权限
```

**解决方案**:
1. 登录 Tushare 查看积分
2. 完成任务获取积分
3. 或升级会员

### 问题 3: 数据库中没有数据

**错误信息**:
```
❌ 错误：数据库中没有 000333.SZ 的财务数据
```

**解决方案**:
```bash
# 运行数据采集
python update_financial_data.py --init
```

### 问题 4: 数据采集中断

**解决方案**:
```bash
# 查看日志找到最后成功的股票
tail -100 update_financial_data.log

# 从该股票继续
python update_financial_data.py --init --resume-from 最后成功的股票代码
```

### 问题 5: 数据库锁定

**错误信息**:
```
database is locked
```

**解决方案**:
1. 确保没有其他程序在访问数据库
2. 关闭所有相关程序
3. 重启 Python 进程

### 问题 6: 内存不足

**解决方案**:
```bash
# 减少线程数
python update_financial_data.py --init --max-workers 2

# 或分批处理
python update_financial_data.py --init --resume-from 000001.SZ
# 处理一部分后中断，再继续
```

---

## 性能优化建议

### 1. 数据采集优化

```bash
# 根据机器性能调整线程数
# 4核CPU: --max-workers 4
# 8核CPU: --max-workers 8

# API 积分充足时可增加限流
# 编辑 update_financial_data.py
# rate_limiter = RateLimiter(max_calls=300, period=60)
```

### 2. 数据库优化

```python
from financial_data_manager import FinancialDataManager

db = FinancialDataManager('database/financial_data.db')

# 定期清理和优化
db.vacuum_database()
```

### 3. 分析优化

```bash
# 只分析需要的年份
python main.py 000333 --years 5

# 不生成 HTML 报告（如果不需要）
# 修改 main.py，注释掉 HTML 生成部分
```

---

## 数据更新建议

### 更新频率

- **初始化**: 仅需一次
- **增量更新**: 每季度一次
- **核心指标**: 每月一次（可选）

### 更新时间

| 季度 | 财报截止日 | 建议更新时间 |
|------|-----------|-------------|
| Q1 | 3月31日 | 4月底-5月初 |
| Q2 | 6月30日 | 7月底-8月初 |
| Q3 | 9月30日 | 10月底-11月初 |
| Q4 | 12月31日 | 次年3月底-4月初 |

### 自动化更新

**Linux/Mac crontab**:
```bash
# 每月1号凌晨2点更新
0 2 1 * * cd /path/to/project && python update_financial_data.py --update-latest
```

**Windows 任务计划程序**:
1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每月
4. 操作：启动程序
5. 程序：python
6. 参数：update_financial_data.py --update-latest
7. 起始于：项目目录

---

## 最佳实践

1. **定期备份数据库**
   ```bash
   cp database/financial_data.db database/backup_$(date +%Y%m%d).db
   ```

2. **使用版本控制**
   - 将 config.yaml 加入 .gitignore
   - 只提交代码，不提交数据库

3. **监控数据质量**
   ```python
   db = FinancialDataManager('database/financial_data.db')
   stats = db.get_database_stats()
   # 定期检查记录数是否合理
   ```

4. **日志管理**
   ```bash
   # 定期清理旧日志
   find . -name "*.log" -mtime +30 -delete
   ```

---

**文档版本**: v1.0  
**更新时间**: 2026-03-18
