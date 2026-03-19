# 迁移指南

从旧版本（API 直接调用模式）迁移到新版本（数据库模式）

---

## 概述

### 架构变化

**旧版本（v1.x）**:
```
main.py → TushareClient → Tushare API → 数据分析
```

**新版本（v2.0）**:
```
update_financial_data.py → Tushare API → Database
                                            ↓
                            main.py → Database → 数据分析
```

### 主要改进

1. ✅ **数据采集与分析分离**
2. ✅ **离线分析能力**（main.py 无需 API）
3. ✅ **总股本和分红数据**持久化
4. ✅ **批量更新优化**（多线程 + 限流）
5. ✅ **断点续传支持**

---

## 迁移步骤

### 步骤 1: 备份现有数据

```bash
# 备份旧的输出文件
cp -r data data_backup_$(date +%Y%m%d)

# 备份配置文件
cp config.yaml config.yaml.backup
```

### 步骤 2: 更新代码

```bash
# 拉取最新代码
git pull origin main

# 或下载最新版本
# 解压到项目目录
```

### 步骤 3: 安装新依赖

```bash
# 检查 requirements.txt 是否有新增依赖
pip install -r requirements.txt --upgrade
```

### 步骤 4: 初始化数据库

```bash
# 首次使用需要初始化数据库（采集完成后自动计算年报+TTM核心指标）
python update_financial_data.py --init

# 这会采集所有A股的历史数据
# 时间较长，请耐心等待，可通过 tqdm 进度条查看剩余时间
```

### 步骤 5: 验证迁移

```bash
# 测试分析功能
python main.py 000333

# 检查输出文件是否正常生成
ls -lh data/000333.SZ_*
```

---

## 代码迁移

### 1. 命令行使用

#### 旧版本

```bash
# 旧版本：每次都调用 API
python main.py 000333 --config config.yaml
```

#### 新版本

```bash
# 新版本：先采集数据（一次性）
python update_financial_data.py --init  # 自动指标计算 + tqdm 进度条

# 然后分析（无需 API）
python main.py 000333 --db-path database/financial_data.db
```

### 2. Python API 使用

#### 旧版本

```python
from tushare_client import TushareClient

# 每次都调用 API
client = TushareClient(config_path='config.yaml')
data = client.get_all_financial_data('000333.SZ')

# 获取总股本（每次调用 API）
total_share_data = get_total_share_data(client, '000333.SZ', data['balancesheet'])
```

#### 新版本

```python
from financial_data_manager import FinancialDataManager

# 从数据库读取（无需 API）
db = FinancialDataManager('database/financial_data.db')
balance_df = db.get_financial_data('000333.SZ', 'balancesheet')
income_df = db.get_financial_data('000333.SZ', 'income')

# 读取总股本（从数据库）
total_share_df = db.get_total_share_data('000333.SZ')

# 读取分红数据（从数据库）
dividend_df = db.get_dividend_data('000333.SZ')
```

### 3. 数据采集

#### 旧版本

```python
# 旧版本：没有专门的批量采集工具
# 需要手动循环调用
for stock in stock_list:
    data = client.get_all_financial_data(stock)
    # 保存为文件...
```

#### 新版本

```python
from update_financial_data import FinancialDataUpdater

# 新版本：专业的批量采集工具
updater = FinancialDataUpdater(
    config_path='config.yaml',
    db_path='database/financial_data.db',
    max_workers=4
)

# 批量更新所有股票（内置写入队列 + 进度条）
stocks = updater.get_stock_list()
updater.update_all_stocks(stocks)

# 或单只股票
updater.fetch_stock_all_data('000333.SZ', force_update=True)
```

---

## 功能对比

### 1. 总股本数据

#### 旧版本

```python
# 每次都调用 API
total_share_data = get_total_share_data(client, ts_code, balance_df)
# 返回字典：{end_date: total_share}
```

#### 新版本

```python
# 从数据库读取
total_share_df = db.get_total_share_data(ts_code)
# 返回 DataFrame，包含 end_date, total_share, update_time

# 日期范围筛选
total_share_df = db.get_total_share_data(
    ts_code, 
    start_date='20200101',
    end_date='20231231'
)

# 检查是否存在
exists = db.check_total_share_exists(ts_code, '20231231')
```

### 2. 分红数据

#### 旧版本

```python
# 每次都调用 API，保存为 Excel
dividend_df = get_dividend_data(client, ts_code, output_dir)
# 自动保存为 Excel 文件
```

#### 新版本

```python
# 从数据库读取
dividend_df = db.get_dividend_data(ts_code)
# 返回 DataFrame，中文列名

# 可选：保存为 Excel
python main.py 000333 --save-dividend-excel

# 或在代码中
dividend_df.to_excel('dividend.xlsx', index=False)
```

### 3. 财务数据

#### 旧版本

```python
# 每次都调用 API
data = client.get_all_financial_data(ts_code)
balance_df = data['balancesheet']
income_df = data['income']
```

#### 新版本

```python
# 从数据库读取
balance_df = db.get_financial_data(ts_code, 'balancesheet')
income_df = db.get_financial_data(ts_code, 'income')
cashflow_df = db.get_financial_data(ts_code, 'cashflow')
indicator_df = db.get_financial_data(ts_code, 'fina_indicator')

# 支持日期范围筛选
balance_df = db.get_financial_data(
    ts_code, 
    'balancesheet',
    start_date='20200101',
    end_date='20231231'
)
```

---

## 配置文件变化

### 旧版本 config.yaml

```yaml
tushare:
  token: "你的Token"
```

### 新版本 config.yaml

```yaml
tushare:
  token: "你的Token"
  
database:
  path: "database/financial_data.db"
  
update:
  max_workers: 4
  rate_limit: 200
  retry_times: 3
```

**注意**: 旧配置文件仍然兼容，新增字段有默认值。

---

## 数据库结构

### 新增表

| 表名 | 说明 | 主要字段 |
|------|------|---------|
| `total_share` | 总股本数据 | ts_code, end_date, total_share |
| `dividend` | 分红数据 | ts_code, end_date, cash_div, stk_div |

### 现有表变化

| 表名 | 变化 |
|------|------|
| `balancesheet` | 无变化 |
| `income` | 无变化 |
| `cashflow` | 无变化 |
| `fina_indicator` | 无变化 |
| `stock_list` | 无变化 |

---

## 常见问题

### Q1: 旧版本的数据文件还能用吗？

**答**: 可以，但建议迁移到数据库。

```python
# 读取旧的 CSV 文件
import pandas as pd
balance_df = pd.read_csv('data/000333.SZ_balancesheet.csv')

# 保存到数据库
from financial_data_manager import FinancialDataManager
db = FinancialDataManager('database/financial_data.db')

# 需要将 DataFrame 转换为合适的格式
# 然后调用 save_financial_data
```

### Q2: 必须重新采集所有数据吗？

**答**: 是的，首次使用需要运行 `--init`。

但如果你已经有部分数据库，可以使用 `--resume-from` 继续。

### Q3: 旧版本的脚本还能用吗？

**答**: 
- `tushare_client.py`: 仍然可用
- `main.py`: 已重构，不再依赖 TushareClient
- 自定义脚本: 需要根据新 API 调整

### Q4: 如何保持两个版本并存？

**答**: 
```bash
# 创建新分支
git checkout -b v2.0

# 或使用不同目录
cp -r project project_v2
cd project_v2
# 在这里使用新版本
```

### Q5: 数据库占用多少空间？

**答**: 
- 约 5000 只股票
- 每只股票约 10 年数据
- 预计 2-5 GB

### Q6: 可以自定义数据库路径吗？

**答**: 可以

```bash
# 命令行指定
python update_financial_data.py --init --db-path /path/to/db
python main.py 000333 --db-path /path/to/db

# 或修改 config.yaml
database:
  path: "/path/to/db"
```

---

## 性能对比

### 数据获取速度

| 操作 | 旧版本 | 新版本 | 提升 |
|------|--------|--------|------|
| 单只股票分析 | ~30秒 | ~2秒 | 15x |
| 10只股票分析 | ~5分钟 | ~20秒 | 15x |
| 100只股票分析 | ~50分钟 | ~3分钟 | 16x |

**注**: 新版本首次需要初始化数据库（一次性成本）

### API 调用次数

| 操作 | 旧版本 | 新版本 | 节省 |
|------|--------|--------|------|
| 单只股票分析 | ~20次 | 0次 | 100% |
| 重复分析 | 每次~20次 | 0次 | 100% |
| 批量分析 | N×20次 | 0次 | 100% |

---

## 回退方案

如果需要回退到旧版本：

```bash
# 1. 切换到旧分支
git checkout v1.x

# 2. 或恢复旧文件
git checkout HEAD~10 main.py  # 回退到10个提交前

# 3. 重新安装旧依赖
pip install -r requirements.txt

# 4. 使用旧方式
python main.py 000333 --config config.yaml
```

---

## 最佳实践

### 1. 渐进式迁移

```bash
# 第一天：初始化数据库
python update_financial_data.py --init --max-workers 2

# 需要补齐历史总股本/分红时
python update_financial_data.py --update-dividend-totalshares --max-workers 2

# 第二天：测试分析
python main.py 000333
python main.py 603345

# 第三天：批量分析
# 确认无误后，完全切换到新版本
```

### 2. 保留旧版本备份

```bash
# 创建备份分支
git branch v1-backup

# 或导出旧版本
git archive --format=zip --output=v1-backup.zip v1.x
```

### 3. 数据验证

```python
# 对比新旧版本的数据
import pandas as pd

# 旧版本数据
old_balance = pd.read_csv('data_backup/000333.SZ_balancesheet.csv')

# 新版本数据
from financial_data_manager import FinancialDataManager
db = FinancialDataManager('database/financial_data.db')
new_balance = db.get_financial_data('000333.SZ', 'balancesheet')

# 对比
print("旧版本记录数:", len(old_balance))
print("新版本记录数:", len(new_balance))
```

---

## 技术支持

### 遇到问题？

1. 查看 [用户指南](USER_GUIDE.md)
2. 查看 [常见问题](#常见问题)
3. 查看测试脚本了解用法
4. 提交 Issue

### 反馈建议

欢迎提供反馈和建议，帮助改进迁移体验。

---

**文档版本**: v1.0  
**更新时间**: 2026-03-18  
**适用版本**: v1.x → v2.0
