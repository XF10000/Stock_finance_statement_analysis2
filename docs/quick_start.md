# 快速开始指南

## 一键生成完整财务分析

### 基本用法

只需一条命令，自动生成所有财务分析报告：

```bash
python3 main.py 603345
```

### 自动生成内容

执行上述命令后，系统会自动完成以下三个步骤：

#### 1️⃣ 历史财务报表重构（季度数据）
- ✅ 资产负债表重构
- ✅ 利润表重构（股权价值增加表）
- ✅ 现金流量表重构

#### 2️⃣ 年度财务报表+TTM（覆盖所有历史）
- ✅ 年度资产负债表+TTM
- ✅ 年度利润表+TTM
- ✅ 年度现金流量表+TTM

#### 3️⃣ HTML交互式财务分析报告
- ✅ 利润分析图表
- ✅ 资产负债分析图表
- ✅ 经营效率分析图表（包括ROIC）
- ✅ 支持时间轴缩放、数据点查看等交互功能

### 推荐样例公司

```bash
# 安井食品（推荐样例，2017-2025年数据）
python3 main.py 603345

# 美的集团（2013-2025年数据）
python3 main.py 000333

# 长江电力（2008-2025年数据）
python3 main.py 600900
```

### 输出文件

所有文件保存在 `./data/` 目录：

```
data/
├── 603345.SH_balancesheet_restructured.csv      # 重构后的资产负债表
├── 603345.SH_income_restructured.csv            # 重构后的利润表
├── 603345.SH_cashflow_restructured.csv          # 重构后的现金流量表
├── 603345.SH_balance_sheet_annual_ttm.csv       # 年报+TTM资产负债表
├── 603345.SH_income_statement_annual_ttm.csv    # 年报+TTM利润表
├── 603345.SH_cashflow_statement_annual_ttm.csv  # 年报+TTM现金流量表
└── 603345.SH_financial_report.html              # HTML财务分析报告 ⭐
```

### 查看HTML报告

生成完成后，在浏览器中打开HTML文件：

```bash
open ./data/603345.SH_financial_report.html
```

或者直接双击 `603345.SH_financial_report.html` 文件。

## 执行流程

```
开始
  ↓
1. 从Tushare获取原始财务数据
  ↓
2. 重构三大报表（按文档规则）
  ↓
3. 生成年报+TTM数据（覆盖所有历史）
  ↓
4. 生成HTML交互式报告
  ↓
完成！
```

## 执行时间

- **小公司**（如603345）：约30-60秒
- **中型公司**（如000333）：约60-90秒
- **大公司**（如600900）：约90-120秒

*时间取决于网络速度和历史数据量*

## 重构规则说明

系统严格按照 `docs/财务报表重构规则详细说明.md` 进行重构：

### 资产负债表重构
- 金融资产合计（不包含"其他非流动资产"）
- 长期股权投资
- 经营资产合计
  - 周转性经营投入
  - 长期经营资产（包含"其他非流动资产"）
- 有息债务合计
- 所有者权益合计

### 利润表重构
- 息税前经营利润
- 息前税后经营利润
- 息税前金融资产收益
- 息前税后金融资产收益
- 长期股权投资收益
- 股权价值增加值

### 现金流量表重构
- 自由现金流量分析
- 经营资产自由现金流量
- 长期经营资产扩张性资本支出
- 债务筹资净额

## 关键指标

### ROIC（投资资本回报率）

```
Invested Capital = 所有者权益 + 有息债务 - 金融资产
ROIC = 息前税后经营利润 / 平均Invested Capital
```

### 第三步：初始化数据库
```bash
# 获取全A股数据（首次运行，耗时约2-3小时）
python update_financial_data.py --init
```

**完成！** 现在可以开始分析了。

---

## 📊 使用示例

### 示例1：生成单只股票分析报告
```bash
# 分析美的集团
python main.py 000333

# 查看生成的HTML报告
open docs/000333_SZ_分析报告.html
```

### 示例2：更新最新季度数据
```bash
# 智能增量更新（推荐每周运行）
python update_financial_data.py --update-latest
```

### 示例3：快速更新单只股票
```bash
# 更新单只股票的最新数据
python update_financial_data.py --update-stock 000001

# 生成报告
python main.py 000001
```

---

## 🎯 核心命令速查

### 数据更新命令

| 命令 | 用途 | 耗时 |
|------|------|------|
| `--init` | 首次初始化全A股数据 | 2-3小时 |
| `--update-latest` | 增量更新最新季度 | 30-40分钟 |
| `--update-stock 000001` | 更新单只股票 | <1分钟 |
| `--update-dividend` | 更新分红数据 | 20-30分钟 |
| `--recalculate-all` | 重算核心指标 | 10-15分钟 |

### 报告生成命令

| 命令 | 用途 | 输出 |
|------|------|------|
| `python main.py 000333` | 生成完整分析报告 | HTML + CSV |
| `python fcff_report_generator.py 000333` | 生成FCFF报告 | HTML |
| `python summary_excel_generator.py` | 生成Excel汇总 | Excel |

---

## 💡 推荐工作流

### 首次使用
```bash
# 1. 初始化（只需运行一次）
python update_financial_data.py --init

# 2. 生成报告
python main.py 000333

# 3. 查看报告
open docs/000333_SZ_分析报告.html
```

### 定期维护（每周）
```bash
# 1. 更新最新数据
python update_financial_data.py --update-latest

# 2. 重新生成关注的股票报告
python main.py 000333
python main.py 600519
```

### 快速分析新股票
```bash
# 一条命令完成更新和分析
python update_financial_data.py --update-stock 000001 && python main.py 000001
```

---

## 🔧 常见问题

### Q1: 初始化太慢怎么办？
**A**: 可以使用断点续传：
```bash
# 如果中断了，从指定股票继续
python update_financial_data.py --init --resume 000333
```

### Q2: 如何加快更新速度？
**A**: 调整并发线程数：
```bash
# 增加到8个线程（默认5个）
python update_financial_data.py --update-latest --workers 8
```

### Q3: 股票代码需要带后缀吗？
**A**: 不需要，系统会自动补全：
```bash
# 这两种写法都可以
python main.py 000333
python main.py 000333.SZ
```

### Q4: 如何查看更新日志？
**A**: 日志文件位置：
```bash
# 查看最新日志
tail -f update_financial_data.log
```

### Q5: 数据库在哪里？
**A**: 数据库文件：
```
database/financial_data.db  # 约1-2GB
```

---

## 📚 进阶使用

### 指定季度更新
```bash
# 更新特定季度的数据
python update_financial_data.py --update-latest --quarter 20241231
```

### 完整更新单只股票
```bash
# 重新获取该股票的全部历史数据
python update_financial_data.py --update-stock 000001 --full
```

### 不自动计算指标
```bash
# 只更新数据，不计算指标
python update_financial_data.py --update-latest --no-indicators
```

---

## 🎓 学习资源

### 文档
- `README.md` - 完整使用说明
- `FEATURES.md` - 功能清单
- `CODE_REVIEW_SUMMARY.md` - 代码架构说明
- `数据库更新说明.md` - 数据库详细说明

### 示例股票
推荐用于测试的股票：
- `000333` - 美的集团（数据完整）
- `600519` - 贵州茅台（数据完整）
- `600900` - 长江电力（数据完整）
- `603345` - 安井食品（数据完整）

---

## ⚠️ 注意事项

1. **API限流**：Tushare限制150次/分钟，系统已自动处理
2. **磁盘空间**：确保有至少2GB可用空间
3. **网络连接**：初始化需要稳定的网络连接
4. **数据备份**：建议定期备份 `database/` 目录

---

## 🆘 获取帮助

### 查看命令帮助
```bash
# 查看所有可用参数
python update_financial_data.py --help
python main.py --help
```

### 检查系统状态
```bash
# 查看数据库统计
python -c "from financial_data_manager import FinancialDataManager; \
           db = FinancialDataManager('database/financial_data.db'); \
           print(db.get_database_stats())"
```

---

**开始使用吧！** 🎉

如有问题，请查看详细文档或检查日志文件。保存在哪里？

默认保存在 `./data/` 目录，可通过 `--output-dir` 参数修改：

```bash
python3 main.py 603345 --output-dir ./my_data

### 4. 如何验证数据正确性？

运行验证脚本：

```bash
# 验证600900（长江电力）
python3 verify_600900.py

# 验证Invested Capital计算
python3 check_invested_capital.py

# 生成最终验证报告
python3 final_verification_report.py
```

## 技术文档

- `docs/财务报表重构规则详细说明.md` - 重构规则详细说明
- `docs/实现说明.md` - 实现决策和差异说明
- `README.md` - 完整使用文档

## 下一步

1. **查看HTML报告**：在浏览器中打开生成的HTML文件
2. **分析CSV数据**：使用Excel或Python进一步分析重构后的数据
3. **对比不同公司**：生成多个公司的报告进行横向对比

---

**提示**：首次运行需要配置Tushare Token，详见 `README.md`
