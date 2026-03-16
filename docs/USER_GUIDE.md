# 用户使用手册 - 股票财务报表分析系统

## 目录

1. [快速开始](#快速开始)
2. [安装配置](#安装配置)
3. [基础使用](#基础使用)
4. [高级功能](#高级功能)
5. [报告解读](#报告解读)
6. [常见问题](#常见问题)
7. [使用技巧](#使用技巧)

---

## 快速开始

### 三步上手

**第一步：安装依赖**

```bash
# 进入项目目录
cd Stock_finance_statement_analysis2

# 安装Python依赖包
pip install -r requirements.txt
```

**第二步：配置Token**

```bash
# 复制配置文件模板
cp config.yaml.example config.yaml

# 编辑config.yaml，填入你的Tushare Token
# 获取Token: https://tushare.pro/register
```

**第三步：运行分析**

```bash
# 分析一只股票（以美的集团为例）
python main.py 000333
```

就这么简单！系统会自动完成数据获取、报表重构、生成分析报告等所有工作。

---

## 安装配置

### 系统要求

- **操作系统**: Windows / macOS / Linux
- **Python版本**: 3.8 或更高
- **内存**: 建议 4GB 以上
- **磁盘空间**: 建议 1GB 以上（用于存储数据）

### 详细安装步骤

#### 1. 安装Python

**Windows用户**:
- 访问 https://www.python.org/downloads/
- 下载并安装Python 3.8+
- 安装时勾选"Add Python to PATH"

**macOS用户**:
```bash
# 使用Homebrew安装
brew install python3
```

**Linux用户**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip
```

#### 2. 安装项目依赖

```bash
# 克隆或下载项目到本地
cd Stock_finance_statement_analysis2

# 安装依赖包
pip install -r requirements.txt

# 如果安装速度慢，可以使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 3. 配置Tushare Token

**获取Token**:

1. 访问 https://tushare.pro/register
2. 注册账号（免费）
3. 登录后在个人中心获取Token

**配置Token**:

```bash
# 复制配置模板
cp config.yaml.example config.yaml

# 编辑config.yaml文件
# 将 YOUR_TUSHARE_TOKEN_HERE 替换为你的实际Token
```

config.yaml示例：
```yaml
tushare:
  token: "你的Token字符串"  # 替换这里
```

#### 4. 验证安装

```bash
# 运行测试命令
python main.py 000333 --years 1

# 如果成功，会在data目录生成分析报告
```

---

## 基础使用

### 股票代码格式

系统支持两种格式：

**简化格式（推荐）**:
```bash
python main.py 000333    # 美的集团（深圳）
python main.py 600519    # 贵州茅台（上海）
python main.py 603345    # 安井食品（上海）
```

系统会自动识别交易所：
- `000`、`002`、`003`、`300`开头 → 深圳交易所（.SZ）
- `600`、`601`、`603`、`605`、`688`开头 → 上海交易所（.SH）

**完整格式**:
```bash
python main.py 000333.SZ
python main.py 600519.SH
```

### 基础命令

#### 1. 分析单只股票（最常用）

```bash
# 获取全部历史数据并生成完整分析报告
python main.py 000333
```

**自动生成内容**:
- ✅ 原始财务报表（CSV格式）
- ✅ 重构后的三大报表
- ✅ 年报+TTM数据
- ✅ HTML交互式财务分析报告
- ✅ 核心指标分析报告

**输出文件**（在`data/`目录）:
```
000333.SZ_balancesheet_restructured.csv          # 重构资产负债表
000333.SZ_income_restructured.csv                # 重构利润表
000333.SZ_cashflow_restructured.csv              # 重构现金流量表
000333.SZ_balance_sheet_annual_ttm.csv           # 年报+TTM资产负债表
000333.SZ_income_statement_annual_ttm.csv        # 年报+TTM利润表
000333.SZ_cashflow_statement_annual_ttm.csv      # 年报+TTM现金流量表
000333.SZ_financial_report.html                  # HTML财务分析报告 ⭐
000333.SZ_核心指标_20250316_152030.html          # 核心指标报告 ⭐
000333.SZ_分红送股.xlsx                          # 分红送股数据
```

#### 2. 指定日期范围

```bash
# 只获取2020-2023年的数据
python main.py 600519 --start-date 20200101 --end-date 20231231
```

#### 3. 指定输出格式

```bash
# 输出Excel格式
python main.py 603345 --format excel

# 同时输出CSV和Excel
python main.py 603345 --format both
```

#### 4. 指定年报年数

```bash
# 只生成最近5年的年报+TTM
python main.py 000333 --years 5

# 生成最近10年（默认）
python main.py 000333 --years 10
```

#### 5. 自定义输出目录

```bash
# 将数据保存到指定目录
python main.py 000333 --output-dir ./my_analysis
```

### 查看分析报告

#### HTML报告（推荐）

**方式1**: 直接双击HTML文件
```
在文件管理器中找到：
data/000333.SZ_financial_report.html
双击打开
```

**方式2**: 使用命令行打开
```bash
# macOS
open data/000333.SZ_financial_report.html

# Windows
start data/000333.SZ_financial_report.html

# Linux
xdg-open data/000333.SZ_financial_report.html
```

#### CSV/Excel报告

使用Excel、WPS或其他电子表格软件打开CSV/Excel文件进行查看和分析。

---

## 高级功能

### 1. 批量分析多只股票

虽然main.py每次只能分析一只股票，但可以使用脚本批量处理：

**创建批量分析脚本** (`batch_analysis.sh`):

```bash
#!/bin/bash
# 批量分析多只股票

stocks=(
    "000333"  # 美的集团
    "600519"  # 贵州茅台
    "603345"  # 安井食品
    "600900"  # 长江电力
)

for stock in "${stocks[@]}"
do
    echo "正在分析: $stock"
    python main.py $stock
    echo "完成: $stock"
    echo "------------------------"
done

echo "批量分析完成！"
```

**运行批量分析**:
```bash
chmod +x batch_analysis.sh
./batch_analysis.sh
```

### 2. 只获取原始数据（不重构）

```bash
# 使用--no-annual-ttm参数跳过重构和报告生成
python main.py 000333 --no-annual-ttm
```

这样只会获取原始财务数据，不进行重构和报告生成，速度更快。

### 3. 使用英文字段名

```bash
# 保留英文字段名（不翻译）
python main.py 000333 --no-translate
```

适合需要与其他系统对接或进行编程分析的场景。

### 4. 使用原始数据格式

```bash
# 不转置数据（保持原始格式：每行一个报告期）
python main.py 000333 --no-transpose
```

原始格式更适合导入数据库或进行程序化处理。

### 5. 组合使用参数

```bash
# 获取最近3年数据，输出Excel格式，保存到custom目录
python main.py 603345 \
    --years 3 \
    --format excel \
    --output-dir ./custom_analysis
```

### 6. 数据库存储与更新

系统支持将财务数据存储到数据库中，便于数据管理、查询和长期跟踪分析。

#### 6.1 配置数据库

**第一步：编辑配置文件**

编辑 `config.yaml`，启用数据库存储：

```yaml
data:
  output_dir: "./data"
  save_csv: true
  save_excel: false
  save_database: true              # 启用数据库存储
  
  database:
    type: "mysql"                  # 数据库类型：sqlite/mysql/postgresql
    host: "localhost"              # 数据库主机
    port: 3306                     # 端口
    username: "stock_user"         # 用户名
    password: "your_password"      # 密码
    database: "stock_finance"      # 数据库名
```

**使用SQLite（推荐新手）**:

```yaml
data:
  save_database: true
  database:
    type: "sqlite"
    path: "./data/stock_data.db"  # SQLite数据库文件路径
```

**第二步：安装数据库驱动**

```bash
# MySQL
pip install pymysql

# PostgreSQL
pip install psycopg2-binary

# SQLite（Python自带，无需安装）
```

**第三步：创建数据库表**

首次使用需要创建数据库表结构。运行初始化脚本：

```bash
# 创建数据库表（假设有init_database.py脚本）
python init_database.py
```

或手动执行SQL脚本（参见技术文档中的表结构）。

#### 6.2 增量更新数据库

推荐使用 `update_market_data.py --update-latest`，系统会自动：
- 识别需要更新的季度（或通过 `--quarter 20241231` 手动指定）
- 跳过已有数据的股票，仅抓取缺失季度
- 完成后自动批量计算核心指标（如无需可加 `--no-indicators`）

```bash
# 自动判断当前应更新的季度
python update_market_data.py --update-latest

# 指定季度 + 关闭指标计算
python update_market_data.py --update-latest --quarter 20241231 --no-indicators

# 使用备用数据库 + 自定义线程数
python update_market_data.py --update-latest --db database/market_data_test.db --workers 10
```

如需定时执行，可在 crontab / 任务计划中调用同一命令。

#### 6.3 全量更新数据库

全量获取全部历史数据，用于首次建库或彻底重建：

```bash
# 首次初始化（自动跳过已有股票）
python update_market_data.py --init

# 强制覆盖所有股票
python update_market_data.py --init --force

# 断点续传
python update_market_data.py --init --resume 600519.SH
```

执行期间会自动限流，多次运行可增量补齐遗漏股票。注意 API 积分和耗时（数小时）。

#### 6.4 重新计算核心指标

在任意时刻可以清空 `core_indicators` 并重新生成：

```bash
# 重算全部历史
python update_market_data.py --recalculate-all

# 仅重算指定季度，如2024Q4
python update_market_data.py --recalculate-all --quarter 20241231
```

该流程采用内存批量算法，约 10-20 分钟完成全A股重算。若只想针对最新更新的股票，可先增量更新，再运行 `--recalculate-all --quarter <目标季度>`。

#### 6.4 增量更新 vs 全量更新对比

| 对比项 | 增量更新 | 全量更新 |
|--------|---------|---------|
| **更新范围** | 最近N天（如90天） | 所有历史数据 |
| **速度** | ⚡ 快（秒级） | 🐢 慢（分钟级） |
| **API消耗** | 💰 少 | 💰💰💰 多 |
| **数据完整性** | 部分更新 | 完整覆盖 |
| **适用场景** | 日常维护 | 首次入库、数据修复 |
| **推荐频率** | 每天/每周 | 每季度/每年 |

#### 6.5 查询数据库数据

**方法1：使用Python查询**

创建 `query_database.py`:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查询数据库示例"""

from database import DatabaseManager
import pandas as pd

def query_latest_data(ts_code):
    """查询最新财务数据"""
    db = DatabaseManager()
    
    query = f"""
    SELECT end_date, roe, roic, grossprofit_margin, netprofit_margin
    FROM fina_indicator
    WHERE ts_code = '{ts_code}'
    ORDER BY end_date DESC
    LIMIT 5
    """
    
    df = pd.read_sql(query, db.engine)
    print(f"\n{ts_code} 最近5期财务指标:")
    print(df.to_string(index=False))
    return df

def query_industry_comparison(industry, end_date):
    """查询行业对比数据"""
    db = DatabaseManager()
    
    query = f"""
    SELECT 
        sb.name,
        fi.roe,
        fi.roic,
        fi.grossprofit_margin
    FROM fina_indicator fi
    JOIN stock_basic sb ON fi.ts_code = sb.ts_code
    WHERE sb.industry = '{industry}'
    AND fi.end_date = '{end_date}'
    ORDER BY fi.roic DESC
    LIMIT 10
    """
    
    df = pd.read_sql(query, db.engine)
    print(f"\n{industry}行业 ROIC Top 10 ({end_date}):")
    print(df.to_string(index=False))
    return df

if __name__ == '__main__':
    # 查询美的集团最新数据
    query_latest_data('000333.SZ')
    
    # 查询家电行业对比
    query_industry_comparison('家用电器', '20231231')
```

**方法2：使用数据库客户端**

使用MySQL Workbench、Navicat、DBeaver等工具直接连接数据库查询。

**常用查询示例**:

```sql
-- 查询某只股票最新财务指标
SELECT * FROM fina_indicator 
WHERE ts_code = '000333.SZ' 
ORDER BY end_date DESC 
LIMIT 1;

-- 查询ROIC大于15%的股票
SELECT sb.name, fi.end_date, fi.roic
FROM fina_indicator fi
JOIN stock_basic sb ON fi.ts_code = sb.ts_code
WHERE fi.roic > 0.15
AND fi.end_date = '20231231'
ORDER BY fi.roic DESC;

-- 查询某行业平均指标
SELECT 
    AVG(roe) as avg_roe,
    AVG(roic) as avg_roic,
    AVG(grossprofit_margin) as avg_gross_margin
FROM fina_indicator fi
JOIN stock_basic sb ON fi.ts_code = sb.ts_code
WHERE sb.industry = '家用电器'
AND fi.end_date = '20231231';
```

#### 6.6 数据库维护

**定期备份**:

```bash
# MySQL备份
mysqldump -u stock_user -p stock_finance > backup_$(date +%Y%m%d).sql

# SQLite备份
cp ./data/stock_data.db ./data/backup/stock_data_$(date +%Y%m%d).db
```

**查看更新日志**:

```sql
-- 查看最近的更新记录
SELECT * FROM data_update_log 
ORDER BY created_at DESC 
LIMIT 10;

-- 查看失败的更新
SELECT * FROM data_update_log 
WHERE status = 'failed' 
ORDER BY created_at DESC;
```

**清理旧数据**:

```sql
-- 删除5年前的数据（谨慎操作）
DELETE FROM fina_indicator 
WHERE end_date < '20190101';
```

#### 6.7 推荐的更新策略

**日常维护策略**:

```
周一至周五（交易日）:
  - 每天早上8点：增量更新（回溯7天）
  - 检查更新日志，确认无失败

季报发布期（4月、8月、10月、次年4月）:
  - 增量更新（回溯90天）
  - 确保获取最新季报数据

每季度末:
  - 全量更新核心关注股票
  - 验证数据完整性

每年末:
  - 全量更新所有股票
  - 数据库备份
```

**自动化脚本示例**:

创建 `auto_update.py`:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""自动更新策略"""

import datetime
from incremental_update import incremental_update_batch
from full_update import full_update_batch

def auto_update():
    """根据日期自动选择更新策略"""
    today = datetime.date.today()
    
    # 核心关注股票
    core_stocks = ['000333.SZ', '600519.SH', '603345.SH']
    
    # 判断是否季度末（3、6、9、12月最后一天后的第一周）
    is_quarter_end = today.month in [4, 7, 10, 1] and today.day <= 7
    
    # 判断是否年末（1月第一周）
    is_year_end = today.month == 1 and today.day <= 7
    
    if is_year_end:
        print("执行年度全量更新...")
        full_update_batch(core_stocks)
    elif is_quarter_end:
        print("执行季度增量更新（90天）...")
        incremental_update_batch(core_stocks, days_back=90)
    else:
        print("执行日常增量更新（7天）...")
        incremental_update_batch(core_stocks, days_back=7)

if __name__ == '__main__':
    auto_update()
```

---

## 报告解读

### HTML财务分析报告

打开`XXX_financial_report.html`后，你会看到：

#### 1. 利润分析部分

**营业收入趋势图**
- 观察收入增长趋势
- 识别收入波动周期
- 对比不同年份的收入水平

**毛利率和净利率趋势**
- 毛利率 = (营业收入 - 营业成本) / 营业收入
- 净利率 = 净利润 / 营业收入
- **解读**: 
  - 毛利率上升 → 产品竞争力增强或成本控制改善
  - 净利率上升 → 整体盈利能力提升

**期间费用率分析**
- 销售费用率、管理费用率、研发费用率
- **解读**: 费用率下降通常是好事，说明费用控制良好

#### 2. 资产负债分析

**资产结构图**
- 金融资产、经营资产、长期股权投资的占比
- **解读**: 
  - 经营资产占比高 → 专注主业
  - 金融资产占比高 → 可能有大量闲置资金

**负债结构图**
- 有息债务、无息负债的占比
- **解读**: 有息债务过高可能增加财务风险

**资产负债率趋势**
- 资产负债率 = 负债总额 / 资产总额
- **解读**: 
  - 一般企业：30%-60%为合理区间
  - 过高（>70%）→ 财务风险大
  - 过低（<20%）→ 可能资金利用效率低

#### 3. 经营效率分析

**ROIC（投资资本回报率）**
- ROIC = 息前税后经营利润 / 平均投资资本
- **解读**: 
  - ROIC > 10% → 优秀
  - ROIC > 15% → 非常优秀
  - ROIC < 5% → 需要关注

**ROE（净资产收益率）**
- ROE = 净利润 / 平均净资产
- **解读**: 
  - ROE > 15% → 优秀
  - ROE > 20% → 非常优秀
  - 持续高ROE是优质公司的标志

### 核心指标报告

打开`XXX_核心指标_XXXXXX.html`后，重点关注：

#### 关键财务指标

**盈利能力指标**:
- 毛利率：反映产品竞争力
- 净利率：反映整体盈利能力
- ROE：反映股东回报水平
- ROIC：反映资本使用效率

**成长性指标**:
- 营业收入增长率
- 净利润增长率
- 总资产增长率

**偿债能力指标**:
- 资产负债率：反映财务杠杆
- 流动比率：反映短期偿债能力
- 速动比率：更严格的短期偿债能力指标

**营运能力指标**:
- 应收账款周转率：收款效率
- 存货周转率：存货管理效率
- 总资产周转率：资产使用效率

### CSV数据文件

#### 重构后的报表文件

**资产负债表** (`XXX_balancesheet_restructured.csv`):
```
项目列：
- 金融资产合计
- 长期股权投资
- 经营资产合计
  - 周转性经营投入合计
  - 长期经营资产合计
- 有息债务合计
- 所有者权益合计
```

**利润表** (`XXX_income_restructured.csv`):
```
项目列：
- 营业收入
- 营业成本
- 毛利率
- 息税前经营利润
- 息前税后经营利润
- 净利润
- 股权价值增加值
```

**现金流量表** (`XXX_cashflow_restructured.csv`):
```
项目列：
- 经营活动现金流量净额
- 经营资产自由现金流量
- 长期经营资产扩张性资本支出
- 债务筹资净额
```

#### 年报+TTM文件

文件名包含`annual_ttm`的文件，包含：
- 历史年报数据（如2015-2024）
- 最新一期TTM数据（如2025Q3-TTM）

**TTM含义**: Trailing Twelve Months（最近12个月）
- 用于更准确反映公司最新经营状况
- 消除季节性波动影响

---

## 常见问题

### Q1: 提示"配置文件不存在"怎么办？

**A**: 需要先创建配置文件

```bash
# 复制配置模板
cp config.yaml.example config.yaml

# 编辑config.yaml，填入你的Token
```

### Q2: 提示"Token错误"或"权限不足"？

**A**: 检查Token是否正确

1. 登录 https://tushare.pro
2. 在个人中心查看Token
3. 确认Token已正确复制到config.yaml
4. 检查积分是否足够（部分接口需要积分）

### Q3: 数据为空或部分数据缺失？

**可能原因**:

1. **股票代码错误**: 检查代码格式是否正确
2. **日期范围无数据**: 扩大日期范围或不指定日期
3. **积分不足**: 升级Tushare积分等级
4. **新上市公司**: 历史数据较少

**解决方法**:
```bash
# 不指定日期，获取全部历史数据
python main.py 000333

# 检查输出日志，查看具体错误信息
```

### Q4: 运行速度慢怎么办？

**优化方法**:

1. **限制年数**:
```bash
python main.py 000333 --years 5  # 只获取5年数据
```

2. **跳过报告生成**:
```bash
python main.py 000333 --no-annual-ttm
```

3. **调整API请求间隔**:
```yaml
# config.yaml
tushare:
  api:
    request_interval: 0.2  # 如果积分高，可以减小间隔
```

### Q5: 如何获取更多积分？

**获取积分方法**:

1. **注册认证**: 完成实名认证
2. **每日签到**: 每天登录签到
3. **分享推广**: 邀请好友注册
4. **捐赠支持**: 捐赠获取积分
5. **数据贡献**: 贡献数据或代码

详见: https://tushare.pro/document/1?doc_id=13

### Q6: 生成的HTML报告打不开？

**解决方法**:

1. **检查文件是否存在**: 确认data目录下有HTML文件
2. **使用不同浏览器**: 尝试Chrome、Firefox、Safari
3. **检查文件权限**: 确保文件有读取权限
4. **查看错误日志**: 检查是否有报告生成失败的错误

### Q7: 如何对比多只股票？

**方法1**: 分别生成报告后手动对比

```bash
python main.py 000333  # 美的集团
python main.py 600519  # 贵州茅台
# 然后打开各自的HTML报告对比
```

**方法2**: 使用Excel汇总

```bash
# 将多只股票的CSV数据导入Excel
# 使用Excel的图表功能进行对比分析
```

### Q8: 数据与财报不一致？

**可能原因**:

1. **数据更新时间**: Tushare数据可能有延迟
2. **数据版本**: 公司可能更正过财报（update_flag）
3. **计算口径**: 重构后的数据计算口径可能不同

**验证方法**:
- 对比原始数据文件（XXX_balancesheet.csv等）
- 查看公司官方财报
- 检查update_flag字段

---

## 使用技巧

### 技巧1: 快速筛选优质公司

使用核心指标报告，关注以下指标：

```
优质公司特征：
✓ ROIC > 15%（持续）
✓ ROE > 20%（持续）
✓ 毛利率 > 30%
✓ 净利率 > 10%
✓ 营收增长率 > 15%
✓ 资产负债率 < 50%
✓ 经营现金流 > 净利润
```

### 技巧2: 识别财务风险

**警示信号**:
- 资产负债率 > 70%
- 流动比率 < 1
- 经营现金流持续为负
- 应收账款增长远超营收增长
- 存货周转率持续下降

### 技巧3: 行业对比分析

```bash
# 分析同行业多家公司
python main.py 000333  # 美的集团（家电）
python main.py 000651  # 格力电器（家电）
python main.py 002050  # 三花智控（家电零部件）

# 对比它们的：
# - ROIC水平
# - 毛利率
# - 费用率
# - 资产负债率
```

### 技巧4: 定期跟踪

建议每季度更新一次数据：

```bash
# 创建定期更新脚本
# update_quarterly.sh

#!/bin/bash
DATE=$(date +%Y%m%d)
echo "开始季度更新: $DATE"

# 更新关注的股票列表
python main.py 000333
python main.py 600519
python main.py 603345

echo "季度更新完成！"
```

### 技巧5: 数据导出到Excel进行深度分析

```bash
# 导出Excel格式
python main.py 000333 --format excel

# 在Excel中可以：
# 1. 创建自定义图表
# 2. 进行趋势分析
# 3. 建立财务模型
# 4. 进行敏感性分析
```

### 技巧6: 结合其他信息源

本系统提供财务数据分析，建议结合：

- **公司公告**: 了解重大事项
- **行业研报**: 了解行业趋势
- **新闻资讯**: 了解公司动态
- **实地调研**: 了解经营情况

### 技巧7: 建立自己的分析模板

```bash
# 创建分析笔记模板
# analysis_template.md

## 公司名称: XXX
## 分析日期: YYYY-MM-DD

### 1. 基本面分析
- ROIC: 
- ROE: 
- 毛利率: 
- 净利率: 

### 2. 成长性分析
- 营收增长率: 
- 净利润增长率: 

### 3. 财务健康度
- 资产负债率: 
- 流动比率: 
- 现金流状况: 

### 4. 估值分析
- PE: 
- PB: 
- PS: 

### 5. 投资结论
- 优势: 
- 风险: 
- 建议: 
```

---

## 进阶学习

### 推荐阅读

**财务分析书籍**:
1. 《财务报表分析与股票估值》- 郭永清
2. 《巴菲特的护城河》- 帕特·多尔西
3. 《聪明的投资者》- 本杰明·格雷厄姆

**在线资源**:
- Tushare官方文档: https://tushare.pro/document/2
- 财务分析教程: [相关链接]
- 投资理论学习: [相关链接]

### 参与贡献

如果你发现bug或有改进建议：

1. 提交Issue: [GitHub Issues链接]
2. 贡献代码: Fork项目并提交Pull Request
3. 完善文档: 帮助改进用户文档

---

## 获取帮助

### 技术支持

- **文档**: 查看`docs/`目录下的技术文档
- **示例**: 参考`快速开始.md`中的示例
- **社区**: [社区论坛链接]

### 联系方式

- **Email**: [联系邮箱]
- **GitHub**: [项目地址]
- **微信群**: [二维码]

---

## 附录

### A. 常用股票代码

**白酒行业**:
- 600519: 贵州茅台
- 000858: 五粮液
- 000568: 泸州老窖

**家电行业**:
- 000333: 美的集团
- 000651: 格力电器
- 600690: 海尔智家

**食品行业**:
- 603345: 安井食品
- 600887: 伊利股份
- 000895: 双汇发展

**电力行业**:
- 600900: 长江电力
- 600886: 国投电力

### B. 财务指标速查表

| 指标 | 计算公式 | 优秀标准 |
|------|---------|---------|
| ROIC | 息前税后经营利润/平均投资资本 | >15% |
| ROE | 净利润/平均净资产 | >20% |
| 毛利率 | (营收-成本)/营收 | >30% |
| 净利率 | 净利润/营收 | >10% |
| 资产负债率 | 负债/资产 | 30-60% |
| 流动比率 | 流动资产/流动负债 | >1.5 |
| 速动比率 | (流动资产-存货)/流动负债 | >1 |

### C. 快捷命令参考

```bash
# 基础分析
python main.py <股票代码>

# 指定年数
python main.py <股票代码> --years 5

# Excel格式
python main.py <股票代码> --format excel

# 指定日期
python main.py <股票代码> --start-date 20200101 --end-date 20231231

# 自定义目录
python main.py <股票代码> --output-dir ./my_data

# 组合使用
python main.py <股票代码> --years 3 --format excel --output-dir ./analysis
```

---

**祝您投资顺利！**

*最后更新: 2025-03-16*
