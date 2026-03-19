# 股票财务数据分析系统

基于 Tushare API 的股票财务数据采集与分析系统，采用**数据采集与分析分离**的架构设计，支持完整的财务报表数据获取、本地存储和深度分析。

## 🎯 核心特性

### 数据采集层
- ✅ 获取完整的财务数据（包括默认隐藏字段）
- ✅ 支持四大财务报表：资产负债表、利润表、现金流量表、财务指标表
- ✅ **总股本数据**：自动获取历年总股本数据
- ✅ **分红数据**：完整的分红送股记录
- ✅ 批量更新支持（多线程 + API 限流）
- ✅ 增量更新支持（只更新最新季度）
- ✅ 本地数据库持久化存储

### 数据分析层
- ✅ **完全离线分析**：无需 Tushare API，从本地数据库读取
- ✅ 财务报表重构（资产负债表、利润表、现金流量表）
- ✅ 年报+TTM 数据生成
- ✅ HTML 交互式财务分析报告
- ✅ 总股本数据自动集成到资产负债表
- ✅ 分红数据导出

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Tushare API                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          update_financial_data.py (数据采集层)          │
│  - 获取财务四表                                          │
│  - 获取总股本数据                                        │
│  - 获取分红数据                                          │
│  - API 限流控制                                          │
│  - 批量/增量更新                                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│      financial_data_manager.py (数据访问层)             │
│  - SQLite 数据库管理                                     │
│  - 数据 CRUD 操作                                        │
│  - 7张表：财务四表 + 总股本 + 分红 + 股票列表            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              main.py (数据分析层)                        │
│  - 从数据库读取数据                                      │
│  - 财务报表重构                                          │
│  - 年报+TTM 生成                                         │
│  - HTML 报告生成                                         │
└─────────────────────────────────────────────────────────┘
```

## 📦 安装

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Tushare Token

```bash
# 复制配置文件模板
cp config.yaml.example config.yaml

# 编辑 config.yaml，填入你的 Tushare Token
# tushare:
#   token: "你的Token"
```

## 🚀 快速开始

### 方式一：完整流程（推荐）

```bash
# 步骤 1: 初始化数据库并采集所有A股数据（仅需一次）
python update_financial_data.py --init  # 数据采集完成后会自动计算年报+TTM核心指标

# 步骤 2: 分析任意股票（无需 API，完全离线）
python main.py 000333  # 美的集团
python main.py 603345  # 安井食品
python main.py 600900  # 长江电力
```

### 方式二：增量更新

```bash
# 定期更新最新季度数据（含新的 tqdm 进度条）
python update_financial_data.py --update-latest

# 如需补齐缺失的总股本/分红数据
python update_financial_data.py --update-dividend-totalshares

# 然后分析
python main.py 000333
```

## 📖 详细使用说明

### 1. 数据采集（update_financial_data.py）

#### 全量初始化（首次使用）

```bash
# 采集所有A股的全部历史数据
python update_financial_data.py --init  # 自动计算所有核心指标

# 指定线程数（默认4）
python update_financial_data.py --init --max-workers 8

# 从某只股票继续（断点续传）
python update_financial_data.py --init --resume-from 000333.SZ
```

**说明**:
- 首次运行需要较长时间（取决于股票数量和 API 积分）
- 自动创建数据库：`database/financial_data.db`
- 包含：财务四表 + 总股本 + 分红数据
- 支持断点续传，中断后可继续

#### 增量更新（定期维护）

```bash
# 更新所有股票的最新季度数据
python update_financial_data.py --update-latest

# 指定目标季度
python update_financial_data.py --update-latest --target-quarter 20231231
```

**说明**:
- 自动判断当前应更新的季度
- 只更新缺失的数据，避免重复
- 如需补齐总股本/分红数据，可额外执行 `--update-dividend-totalshares`
- 适合定期运行（如每季度财报发布后）

#### 补齐总股本 & 分红数据（可选）

```bash
# 仅补齐缺失的总股本和分红（智能跳过已有数据）
python update_financial_data.py --update-dividend-totalshares
```

**说明**:
- 适合老数据库或增量更新后补齐历史分红/总股本
- 自动检测缺失的报告期，只调用必要的 API
- 同样配备 tqdm 进度条显示成功/跳过数量

#### 重新计算核心指标

```bash
# 重新计算所有股票的核心指标和百分位排名
python update_financial_data.py --recalculate-all
```

> **提示**: `--init` 在采集完成后会自动执行年报与 TTM 指标计算，大多数场景无需再运行 `--recalculate-all`。

### 2. 数据分析（main.py）

#### 基本用法

```bash
# 分析单只股票（自动生成所有报表）
python main.py 000333

# 指定数据库路径
python main.py 000333 --db-path database/financial_data.db

# 指定输出目录
python main.py 000333 --output-dir ./output
```

#### 高级选项

```bash
# 筛选日期范围
python main.py 000333 --start-date 20200101 --end-date 20231231

# 保存分红数据为 Excel
python main.py 000333 --save-dividend-excel

# 指定年报年数
python main.py 000333 --years 10

# 不生成年报+TTM
python main.py 000333 --no-annual-ttm

# 指定输出格式
python main.py 000333 --format excel  # 或 csv, both
```

#### 输出文件

```
data/
├── 000333.SZ_balancesheet_restructured.csv      # 重构资产负债表
├── 000333.SZ_income_restructured.csv            # 重构利润表
├── 000333.SZ_cashflow_restructured.csv          # 重构现金流量表
├── 000333.SZ_balance_sheet_annual_ttm.csv       # 年报+TTM资产负债表
├── 000333.SZ_income_statement_annual_ttm.csv    # 年报+TTM利润表
├── 000333.SZ_cashflow_statement_annual_ttm.csv  # 年报+TTM现金流量表
├── 000333.SZ_分红送股.xlsx                      # 分红数据（可选）
└── 000333.SZ_financial_report.html              # HTML分析报告 ⭐
```

## 💾 数据库结构

### 数据库文件
- 路径：`database/financial_data.db`
- 类型：SQLite 3
- 模式：WAL（支持并发读写）

### 数据表

| 表名 | 说明 | 主要字段 |
|------|------|---------|
| `stock_list` | 股票列表 | ts_code, name, industry, market |
| `balancesheet` | 资产负债表 | ts_code, end_date, data (JSON) |
| `income` | 利润表 | ts_code, end_date, data (JSON) |
| `cashflow` | 现金流量表 | ts_code, end_date, data (JSON) |
| `fina_indicator` | 财务指标表 | ts_code, end_date, data (JSON) |
| `total_share` | 总股本数据 | ts_code, end_date, total_share |
| `dividend` | 分红数据 | ts_code, end_date, cash_div, stk_div |

## 🔧 Python API 使用

### 数据采集

```python
from update_financial_data import FinancialDataUpdater

# 初始化更新器
updater = FinancialDataUpdater(
    config_path='config.yaml',
    db_path='database/financial_data.db',
    max_workers=4
)

# 获取单只股票数据
updater.fetch_stock_all_data('000333.SZ', force_update=True)

# 批量更新
stocks = updater.get_stock_list()
updater.update_all_stocks(stocks)
```

### 数据访问

```python
from financial_data_manager import FinancialDataManager

# 初始化数据库管理器
db = FinancialDataManager('database/financial_data.db')

# 读取财务数据
balance_df = db.get_financial_data('000333.SZ', 'balancesheet')
income_df = db.get_financial_data('000333.SZ', 'income')

# 读取总股本数据
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
```

## 📊 股票代码格式

### 简化格式（推荐）

```bash
python main.py 000333    # 自动识别为 000333.SZ
python main.py 600519    # 自动识别为 600519.SH
```

**自动判断规则**:
- `000`, `002`, `003`, `300` 开头 → `.SZ`（深圳）
- `600`, `601`, `603`, `605`, `688` 开头 → `.SH`（上海）

### 完整格式

```bash
python main.py 000333.SZ
python main.py 600519.SH
```

## ⚙️ 配置说明

### config.yaml

```yaml
tushare:
  token: "你的Tushare Token"
  
database:
  path: "database/financial_data.db"
  
update:
  max_workers: 4          # 并发线程数
  rate_limit: 200         # API 调用频率限制（次/分钟）
  retry_times: 3          # 失败重试次数
```

## 🧪 测试

### 运行所有测试

```bash
# Phase 1: 数据库表结构测试
python test_phase1_database.py

# Phase 2: 数据管理方法测试
python test_phase2_methods.py

# Phase 3: 数据采集功能测试（需要 API）
python test_phase3_update.py

# Phase 4: main.py 重构测试
python test_phase4_main.py

# Phase 5: 综合集成测试
python test_phase5_integration.py
```

## 📁 项目结构

```
Stock_finance_statement_analysis2/
├── config.yaml                      # 配置文件
├── requirements.txt                 # Python 依赖
│
├── update_financial_data.py         # 数据采集脚本 ⭐
├── financial_data_manager.py        # 数据库管理器 ⭐
├── main.py                          # 数据分析入口 ⭐
│
├── tushare_client.py                # Tushare API 客户端
├── balance_sheet_restructure.py    # 资产负债表重构
├── income_statement_restructure.py # 利润表重构
├── cashflow_statement_restructure.py # 现金流量表重构
├── annual_report_generator.py      # 年报+TTM 生成器
├── html_report_generator.py        # HTML 报告生成器
│
├── database/                        # 数据库目录
│   └── financial_data.db           # SQLite 数据库
│
├── data/                            # 数据输出目录
├── docs/                            # 文档目录
└── tests/                           # 测试脚本
    ├── test_phase1_database.py
    ├── test_phase2_methods.py
    ├── test_phase3_update.py
    ├── test_phase4_main.py
    └── test_phase5_integration.py
```

## ❓ 常见问题

### 1. 首次使用需要做什么？

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 Token
cp config.yaml.example config.yaml
# 编辑 config.yaml，填入 Token

# 3. 初始化数据库
python update_financial_data.py --init

# 4. 分析股票
python main.py 000333
```

### 2. 数据库在哪里？

默认路径：`database/financial_data.db`

可通过 `--db-path` 参数指定其他路径。

### 3. 如何更新数据？

```bash
# 增量更新最新季度
python update_financial_data.py --update-latest

# 强制更新某只股票
python update_financial_data.py --init --resume-from 000333.SZ
```

### 4. main.py 需要 API 吗？

**不需要**！main.py 完全从本地数据库读取，可离线运行。

只有 update_financial_data.py 需要 Tushare API。

### 5. 数据采集失败怎么办？

- 检查 Token 是否正确
- 检查 API 积分是否足够
- 使用 `--resume-from` 断点续传
- 减少 `--max-workers` 线程数

### 6. 如何查看数据库统计？

```python
from financial_data_manager import FinancialDataManager

db = FinancialDataManager('database/financial_data.db')
stats = db.get_database_stats()
print(stats)
```

## 🔄 数据更新策略

### 推荐方案

```bash
# 每季度财报发布后运行一次
python update_financial_data.py --update-latest
```

### 更新时间建议

- Q1 财报（3月31日）：4月底-5月初
- Q2 财报（6月30日）：7月底-8月初  
- Q3 财报（9月30日）：10月底-11月初
- Q4 财报（12月31日）：次年3月底-4月初

## 📚 参考文档

- [Tushare 官方文档](https://tushare.pro/document/2)
- [项目开发计划](DEVELOPMENT_PLAN.md)
- [使用指南](USER_GUIDE.md)
- [迁移指南](MIGRATION_GUIDE.md)

## 🎓 技术亮点

1. **架构分离**：数据采集与分析完全解耦
2. **离线分析**：main.py 无需 API，可离线运行
3. **数据完整**：包含总股本和分红数据
4. **批量高效**：多线程 + API 限流 + 断点续传
5. **线程安全**：数据库 WAL 模式 + 线程本地连接
6. **测试完善**：5个阶段的完整测试覆盖

## 📄 License

MIT License

---

**版本**: v2.0  
**更新时间**: 2026-03-18  
**重构完成**: Phase 1-6 全部完成 ✅
