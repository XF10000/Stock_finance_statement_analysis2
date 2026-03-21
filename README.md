# A股财务数据分析系统

基于 Tushare 的全A股财务数据获取、存储、分析和可视化系统。

## ✨ 功能特点

### 数据管理
- 自动获取全A股财务四表（资产负债表、利润表、现金流量表、财务指标）及分红数据
- 本地 SQLite 数据库存储，支持 5,100+ 只股票
- 智能增量更新：批量检查缺失数据，按需调用 API
- 股票代码自动补全（支持不带交易所后缀的6位代码）
- 多线程并发获取 + API 限流控制（150次/分钟）
- 断点续传支持

### 数据分析
- 5大核心指标：应收账款周转率、毛利率、长期资产周转率、净营运资本比率、经营现金流比率
- 年报 + TTM（滚动12个月）双视角计算
- 全市场分位数排名（基于同期所有A股）
- 公司特定重分类规则支持（如融资租赁资产调整）

### 报告生成
- HTML 交互式财务分析报告（ECharts 图表）
- 三大报表重构（股权价值增加表、FCFF 现金流）
- 年报 + TTM 汇总 CSV
- 核心指标趋势 + 市场分位数对比报告

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`，填入 Tushare Token：

```yaml
tushare:
  token: "your_token_here"

restructure:
  equity_cost_rate: 0.08   # 股权资本成本率，用于利润表重构
```

### 3. 初始化数据库（首次运行）

```bash
python update_financial_data.py --init
```

获取全A股完整历史财务数据（约5,100只股票），支持断点续传：

```bash
python update_financial_data.py --init --resume 000333
```

### 4. 生成单股分析报告

```bash
python3 main.py 000333    # 支持6位代码（自动补全交易所后缀）
python3 main.py 000333.SZ # 也支持完整格式
```

---

## 📊 单股分析报告（main.py）

一条命令自动生成：
1. 三大报表重构（资产负债表、股权价值增加表、FCFF 现金流）
2. 年报 + TTM 汇总报表（覆盖所有历史年份）
3. HTML 交互式财务分析报告
4. 核心指标分析报告（含市场分位数）

**输出文件**：
```
data/
├── {ts_code}_balancesheet_restructured.csv      # 重构资产负债表
├── {ts_code}_income_restructured.csv            # 重构利润表（股权价值增加表）
├── {ts_code}_cashflow_restructured.csv          # 重构现金流量表
├── {ts_code}_balance_sheet_annual_ttm.csv       # 年报+TTM 资产负债表
├── {ts_code}_income_statement_annual_ttm.csv    # 年报+TTM 利润表
├── {ts_code}_cashflow_statement_annual_ttm.csv  # 年报+TTM 现金流量表
├── {ts_code}_financial_report.html              # HTML 财务分析报告 ⭐
└── {ts_code}_核心指标_{日期}.html               # 核心指标报告 ⭐
```

**常用参数**：
```bash
# 指定日期范围
python3 main.py 000333 --start-date 20180101 --end-date 20241231

# 同时输出 Excel
python3 main.py 000333 --format excel

# 指定输出目录
python3 main.py 000333 --output-dir ./reports

# 保存分红数据为 Excel
python3 main.py 000333 --save-dividend-excel

# 使用自定义数据库路径
python3 main.py 000333 --db-path /path/to/financial_data.db
```

---

## 🔄 数据更新（update_financial_data.py）

### 增量更新（推荐定期运行）

```bash
python update_financial_data.py --update-latest
```

自动判断目标季度（根据当前月份）：

| 月份 | 目标季度 |
|------|---------|
| 2–4 月 | 上年 Q4（12/31） |
| 5–7 月 | 本年 Q1（3/31） |
| 8–10 月 | 本年 Q2（6/30） |
| 11–1 月 | 本年 Q3（9/30） |

### 更新单只股票

```bash
# 最新季度（增量）
python update_financial_data.py --update-stock 000001

# 全部历史数据
python update_financial_data.py --update-stock 000001 --full

# 更新分红数据
python update_financial_data.py --update-stock-dividend 000333
```

### 其他操作

```bash
# 更新所有股票的分红数据
python update_financial_data.py --update-dividend

# 强制重新计算所有股票核心指标
python update_financial_data.py --recalculate-all

# 指定季度更新
python update_financial_data.py --update-latest --quarter 20241231

# 调整并发线程数（默认5，建议2-8）
python update_financial_data.py --update-latest --workers 8

# 不自动计算核心指标
python update_financial_data.py --update-latest --no-indicators
```

---

## 🗂️ 股票代码格式

系统自动补全交易所后缀：

```bash
python3 main.py 000333   # → 000333.SZ（深圳）
python3 main.py 600519   # → 600519.SH（上海）
python3 main.py 688981   # → 688981.SH（科创板）
```

判断规则：
- `000`、`002`、`003`、`300` → `.SZ`
- `600`、`601`、`603`、`605`、`688` → `.SH`
- 其余默认 `.SZ`

---

## 🗃️ 数据库结构

SQLite 数据库（`database/financial_data.db`）包含以下表：

| 表名 | 说明 |
|------|------|
| `stock_list` | 全A股列表 |
| `balancesheet` | 资产负债表（JSON Blob） |
| `income` | 利润表（JSON Blob） |
| `cashflow` | 现金流量表（JSON Blob） |
| `fina_indicator` | 财务指标表（JSON Blob） |
| `dividend` | 分红送股数据 |
| `core_indicators` | 5大核心指标 + 市场分位数 |

---

## 📁 项目结构

```
Stock_finance_statement_analysis2/
├── main.py                          # 单股分析入口
├── update_financial_data.py         # 全A股数据更新程序
├── financial_data_manager.py        # 数据库管理核心 + normalize_stock_code
├── financial_data_analyzer.py       # 市场分位数分析
├── core_indicators_analyzer.py      # 5大核心指标计算
├── tushare_client.py                # Tushare API 客户端
├── annual_report_generator.py       # 年报+TTM 生成
├── html_report_generator.py         # HTML 财务分析报告
├── final_report_generator_echarts.py# 核心指标 ECharts 报告
├── balance_sheet_restructure.py     # 资产负债表重构
├── income_statement_restructure.py  # 利润表重构（股权价值增加表）
├── cashflow_statement_restructure.py# 现金流量表重构
├── ttm_generator.py                 # TTM 计算
├── balance_sheet_reclassifier.py    # 公司特定重分类规则
├── field_mapping.py                 # 字段中英文映射
├── config.yaml.example              # 配置文件模板
├── config.yaml                      # 配置文件（含 Token，不入库）
├── requirements.txt                 # Python 依赖
├── pytest.ini                       # 测试配置
├── tests/                           # 测试套件
├── database/                        # SQLite 数据库
├── data/                            # 分析输出（CSV / HTML）
├── logs/                            # 运行日志
└── docs/                            # 字段文档
```

---

## ⚠️ 注意事项

1. **Tushare 积分**：财务四表接口需要一定积分，积分不足会导致数据获取失败
2. **首次初始化耗时**：全A股约5,100只，完整初始化需要数小时，建议分批或使用 `--resume` 断点续传
3. **数据延迟**：Tushare 财务数据通常在财报披露后1-2个工作日更新
4. **API 限流**：系统已内置限流（150次/分钟），无需手动控制

---

## 参考文档

- [Tushare 官方文档](https://tushare.pro/document/2)
- [资产负债表接口](https://tushare.pro/document/2?doc_id=36)
- [利润表接口](https://tushare.pro/document/2?doc_id=33)
- [现金流量表接口](https://tushare.pro/document/2?doc_id=44)
- [财务指标表接口](https://tushare.pro/document/2?doc_id=79)

## License

MIT License
