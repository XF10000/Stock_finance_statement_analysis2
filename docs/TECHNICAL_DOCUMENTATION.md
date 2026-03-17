# 技术文档 - 股票财务报表分析系统

## 目录

1. [项目概述](#项目概述)
2. [系统架构](#系统架构)
3. [核心模块详解](#核心模块详解)
4. [数据流程](#数据流程)
5. [API接口说明](#api接口说明)
6. [数据库设计](#数据库设计)
7. [配置说明](#配置说明)
8. [扩展开发指南](#扩展开发指南)
9. [性能优化](#性能优化)
10. [故障排查](#故障排查)

---

## 项目概述

### 项目简介

股票财务报表分析系统是一个基于Python的财务数据获取、重构和分析工具，主要功能包括：

- 从Tushare API获取上市公司财务数据
- 按照财务分析理论重构三大财务报表
- 生成年报+TTM（最近12个月）数据
- 生成交互式HTML财务分析报告
- 批量处理A股市场数据

### 技术栈

- **Python**: 3.8+
- **核心依赖**:
  - `tushare`: 金融数据接口
  - `pandas`: 数据处理
  - `numpy`: 数值计算
  - `pyyaml`: 配置管理
  - `openpyxl`: Excel文件处理

### 项目特点

1. **完整的字段获取**: 获取所有财务字段（包括默认隐藏字段）
2. **智能数据筛选**: 自动过滤上市前数据，优先使用更新版本数据
3. **财务报表重构**: 按照"资产-资本"结构重构报表
4. **TTM计算**: 自动计算滚动12个月数据
5. **中英文支持**: 自动翻译字段名为中文

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│  命令行接口 (main.py) / 批量处理 (recalculate_all_*.py)      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      业务逻辑层                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 报表重构模块  │  │ TTM生成模块  │  │ 报告生成模块  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 指标分析模块  │  │ 市场分析模块  │  │ 数据管理模块  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      数据访问层                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │         TushareClient (tushare_client.py)        │      │
│  │  - API请求管理  - 数据获取  - 字段翻译  - 缓存   │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      外部接口层                              │
│              Tushare Pro API (tushare.pro)                  │
└─────────────────────────────────────────────────────────────┘
```

### 模块依赖关系

```
main.py
  ├── tushare_client.py
  │     └── field_mapping.py
  ├── balance_sheet_restructure.py
  ├── income_statement_restructure.py
  ├── cashflow_statement_restructure.py
  ├── annual_report_generator.py
  ├── html_report_generator.py
  └── final_report_generator_echarts.py
        └── core_indicators_analyzer.py
```

---

## 核心模块详解

### 1. TushareClient (tushare_client.py)

**功能**: Tushare API客户端，负责数据获取和基础处理

**核心类**: `TushareClient`

**主要方法**:

```python
class TushareClient:
    def __init__(self, config_path: str = "config.yaml")
        """初始化客户端，加载配置"""
    
    def get_fina_indicator(self, ts_code, start_date, end_date, translate=True)
        """获取财务指标表（~180个字段）"""
    
    def get_balancesheet(self, ts_code, start_date, end_date, translate=True)
        """获取资产负债表（~156个字段）"""
    
    def get_income(self, ts_code, start_date, end_date, translate=True)
        """获取利润表（~94个字段）"""
    
    def get_cashflow(self, ts_code, start_date, end_date, translate=True)
        """获取现金流量表（~99个字段）"""
    
    def get_all_financial_data(self, ts_code, start_date, end_date, translate=True)
        """一次性获取所有财务数据"""
    
    def transpose_data(self, df)
        """转置数据：字段纵向（行），时间横向（列）"""
```

**关键特性**:

1. **自动分页**: 处理大数据量时自动分页获取
2. **错误重试**: 最多重试3次，避免网络波动
3. **数据过滤**: 
   - 过滤上市前数据
   - 优先使用`update_flag=1`的更新版本数据
4. **字段翻译**: 自动将英文字段名翻译为中文
5. **请求限流**: 控制API请求频率（默认0.3秒间隔）

**使用示例**:

```python
from tushare_client import TushareClient

# 初始化客户端
client = TushareClient(config_path='config.yaml')

# 获取单个公司数据
data = client.get_all_financial_data('000333.SZ', translate=True)

# 保存数据
client.save_to_csv(data, '000333.SZ', './data', transpose=True)
```

---

### 2. 财务报表重构模块

#### 2.1 资产负债表重构 (balance_sheet_restructure.py)

**功能**: 将传统资产负债表重构为"资产-资本"结构

**核心函数**: `restructure_balance_sheet(df: pd.DataFrame) -> pd.DataFrame`

**重构逻辑**:

```
资产结构：
├── 金融资产合计
│   ├── 货币资金
│   ├── 交易性金融资产
│   ├── 债权投资
│   └── ...
├── 长期股权投资
├── 经营资产合计
│   ├── 周转性经营投入合计
│   │   ├── 营运资产小计
│   │   └── 营运负债小计（减项）
│   └── 长期经营资产合计
│       ├── 固定资产
│       ├── 无形资产
│       └── ...
└── 资产总额

资本结构：
├── 有息债务合计
│   ├── 短期债务
│   └── 长期债务
├── 所有者权益合计
│   ├── 归属于母公司股东权益
│   └── 少数股东权益
└── 资本总额
```

**关键计算**:

```python
# 周转性经营投入 = 营运资产 - 营运负债
working_capital = operating_assets - operating_liabilities

# 经营资产 = 周转性经营投入 + 长期经营资产
total_operating_assets = working_capital + long_term_operating_assets

# 资产总额 = 金融资产 + 长期股权投资 + 经营资产
total_assets = financial_assets + long_term_equity + total_operating_assets
```

**字段映射**: 使用`UNIFIED_FIELD_MAPPING`统一处理中英文字段名

---

#### 2.2 利润表重构 (income_statement_restructure.py)

**功能**: 将传统利润表重构为股权价值增加表

**核心函数**: `restructure_income_statement(df, equity_data, equity_cost_rate=0.08)`

**重构逻辑**:

```
营业收入
- 营业成本
- 期间费用（销售、管理、研发、税金及附加）
- 资产减值损失
+ 其他经营收益
= 息税前经营利润
- 经营利润所得税
= 息前税后经营利润

投资收益
├── 短期投资收益
└── 长期股权投资收益

金融资产收益
├── 利息收入
├── 公允价值变动收益
├── 汇兑收益
└── 其他综合收益
= 息税前金融资产收益
- 金融资产收益所得税
= 息前税后金融资产收益

息税前利润总额 = 息税前经营利润 + 息税前金融资产收益 + 长期股权投资收益
- 真实财务费用
= 税前利润
- 所得税费用
= 净利润
- 股权资本成本
= 股权价值增加值
```

**关键计算**:

```python
# 实际所得税税率
effective_tax_rate = 所得税费用 / (税前利润 - 长期股权投资收益)

# 经营利润所得税
operating_tax = 息税前经营利润 × 实际所得税税率

# 真实财务费用（加回被扣除的利息收入）
real_financial_expense = 财务费用 + 利息收入

# 股权资本成本
equity_cost = 所有者权益合计 × 股权资本成本率（默认8%）
```

---

#### 2.3 现金流量表重构 (cashflow_statement_restructure.py)

**功能**: 重构现金流量表，增加自由现金流分析

**核心函数**: `restructure_cashflow_statement(df_cashflow, income_data, balance_data, income_restructured)`

**重构逻辑**:

```
自由现金流量分析：
├── 口径一收入现金含量 = 销售收到现金 / 营业收入
├── 成本费用付现率 = (购买支付现金/1.17 + 职工支付现金) / 营业总成本
├── 息前税后经营利润现金含量 = 经营现金流 / 息前税后经营利润
└── 净利润现金含量 = 经营现金流 / 净利润

经营资产自由现金流量：
经营现金流 - 非付现成本费用 = 经营资产自由现金流量

资本支出分析：
├── 长期经营资产净投资额 = 购建支付 - 处置收到
├── 长期经营资产扩张性资本支出 = 净投资额 - 折旧摊销
├── 净合并额 = 取得子公司支付 - 处置子公司收到
└── 扩张性资本支出 = 长期资产扩张性支出 + 净合并额

债务筹资分析：
债务筹资净额 = 借款收到 + 发行债券 - 偿还债务 - 偿付利息
```

**关键计算**:

```python
# 偿付利息支付的现金
interest_payment = 利息费用 + (期末应付利息 - 期初应付利息)

# 长期经营资产扩张性资本支出
expansion_capex = 净投资额 - 折旧 - 摊销 - 处置损失 - 报废损失
```

---

### 3. 年报+TTM生成器 (annual_report_generator.py)

**功能**: 生成年报数据和TTM（Trailing Twelve Months）数据

**核心类**: `AnnualReportGenerator`

**TTM计算公式**:

```python
# 对于利润表和现金流量表（期间数据）
TTM = 今年Q累计 - 去年同Q累计 + 去年Q4累计

# 对于资产负债表（时点数据）
TTM = 最新季度数据
```

**使用场景**:

- 当最新数据是Q1/Q2/Q3时，生成TTM列
- 当最新数据是Q4时，直接使用年报数据

**示例**:

```python
# 假设最新数据是2025Q3
# 营业收入TTM = 2025Q3累计 - 2024Q3累计 + 2024年报
TTM_revenue = revenue_2025Q3 - revenue_2024Q3 + revenue_2024_annual
```

---

### 4. 报告生成模块

#### 4.1 HTML财务分析报告 (html_report_generator.py)

**功能**: 生成交互式HTML财务分析报告

**包含图表**:

1. **利润分析**:
   - 营业收入趋势
   - 毛利率、净利率趋势
   - 期间费用率分析

2. **资产负债分析**:
   - 资产结构变化
   - 负债结构变化
   - 资产负债率趋势

3. **经营效率分析**:
   - ROIC（投资资本回报率）
   - ROE（净资产收益率）
   - 周转率指标

**技术实现**: 使用ECharts生成交互式图表

---

#### 4.2 核心指标报告 (final_report_generator_echarts.py)

**功能**: 生成核心财务指标分析报告

**核心指标**:

```python
# ROIC计算
Invested_Capital = 所有者权益 + 有息债务 - 金融资产
ROIC = 息前税后经营利润 / 平均Invested_Capital

# 其他关键指标
- 营业收入增长率
- 净利润增长率
- 毛利率
- 净利率
- 资产负债率
- 流动比率
- 速动比率
```

---

## 数据流程

### 完整数据处理流程

```
1. 数据获取
   ├── 调用Tushare API
   ├── 获取四大财务报表原始数据
   ├── 过滤上市前数据
   ├── 筛选最新版本数据（update_flag）
   └── 翻译字段名为中文

2. 数据转置
   ├── 原始格式：每行一个报告期，字段为列
   └── 转置格式：字段为行，报告期为列

3. 报表重构
   ├── 资产负债表重构（资产-资本结构）
   ├── 利润表重构（股权价值增加表）
   └── 现金流量表重构（自由现金流分析）

4. TTM计算
   ├── 判断最新季度
   ├── 计算TTM数据（如非Q4）
   └── 生成年报+TTM报表

5. 报告生成
   ├── HTML财务分析报告
   ├── 核心指标分析报告
   └── Excel汇总报告

6. 数据保存
   ├── CSV文件
   ├── Excel文件
   └── HTML报告
```

---

## API接口说明

### 主程序接口 (main.py)

**命令行参数**:

```bash
python main.py <股票代码> [选项]

必需参数:
  股票代码              6位数字或带交易所后缀（如：000333 或 600519.SH）

可选参数:
  --start-date DATE    开始日期（YYYYMMDD格式）
  --end-date DATE      结束日期（YYYYMMDD格式）
  --output-dir DIR     输出目录（默认：./data）
  --format FORMAT      输出格式：csv/excel/both（默认：csv）
  --no-transpose       不转置数据
  --no-translate       不翻译字段名
  --config PATH        配置文件路径（默认：config.yaml）
  --no-annual-ttm      不生成年报+TTM数据
  --years N            年报年数（默认：覆盖所有历史）
```

**使用示例**:

```bash
# 基础用法：获取美的集团全部数据
python main.py 000333

# 指定日期范围
python main.py 600519 --start-date 20200101 --end-date 20231231

# 输出Excel格式
python main.py 603345 --format excel

# 指定年报年数
python main.py 000333 --years 5
```

---

### TushareClient API

**初始化**:

```python
from tushare_client import TushareClient

client = TushareClient(config_path='config.yaml')
```

**获取数据**:

```python
# 获取所有财务数据
data = client.get_all_financial_data(
    ts_code='000333.SZ',
    start_date='20200101',  # 可选
    end_date='20231231',    # 可选
    translate=True          # 翻译为中文
)

# 返回字典
{
    'fina_indicator': DataFrame,  # 财务指标表
    'balancesheet': DataFrame,     # 资产负债表
    'income': DataFrame,           # 利润表
    'cashflow': DataFrame          # 现金流量表
}
```

**保存数据**:

```python
# 保存为CSV
client.save_to_csv(data, '000333.SZ', './data', transpose=True)

# 保存为Excel
client.save_to_excel(data, '000333.SZ', './data', transpose=True)
```

---

## 数据库设计

### 数据库概述

系统支持将财务数据存储到数据库中，便于数据管理、查询和分析。支持SQLite、MySQL、PostgreSQL等主流数据库。

### 数据库架构

#### 核心表结构

**1. 股票基本信息表 (stock_basic)**

```sql
CREATE TABLE stock_basic (
    ts_code VARCHAR(20) PRIMARY KEY,      -- 股票代码（如：000333.SZ）
    symbol VARCHAR(10),                    -- 股票简称代码
    name VARCHAR(50),                      -- 股票名称
    area VARCHAR(20),                      -- 地域
    industry VARCHAR(50),                  -- 所属行业
    market VARCHAR(10),                    -- 市场类型（主板/创业板等）
    list_date DATE,                        -- 上市日期
    is_hs VARCHAR(2),                      -- 是否沪深港通标的
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_stock_industry ON stock_basic(industry);
CREATE INDEX idx_stock_list_date ON stock_basic(list_date);
```

**2. 财务指标表 (fina_indicator)**

```sql
CREATE TABLE fina_indicator (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,         -- 股票代码
    end_date DATE NOT NULL,                -- 报告期
    ann_date DATE,                         -- 公告日期
    
    -- 每股指标
    eps DECIMAL(10,4),                     -- 基本每股收益
    bps DECIMAL(10,4),                     -- 每股净资产
    
    -- 盈利能力
    roe DECIMAL(10,4),                     -- 净资产收益率
    roa DECIMAL(10,4),                     -- 总资产报酬率
    roic DECIMAL(10,4),                    -- 投资资本回报率
    
    -- 营运能力
    ar_turn DECIMAL(10,4),                 -- 应收账款周转率
    inv_turn DECIMAL(10,4),                -- 存货周转率
    assets_turn DECIMAL(10,4),             -- 总资产周转率
    
    -- 偿债能力
    current_ratio DECIMAL(10,4),           -- 流动比率
    quick_ratio DECIMAL(10,4),             -- 速动比率
    debt_to_assets DECIMAL(10,4),          -- 资产负债率
    
    -- 利润率
    grossprofit_margin DECIMAL(10,4),      -- 销售毛利率
    netprofit_margin DECIMAL(10,4),        -- 销售净利率
    
    -- 成长能力
    revenue_yoy DECIMAL(10,4),             -- 营业收入同比增长率
    netprofit_yoy DECIMAL(10,4),           -- 净利润同比增长率
    
    update_flag VARCHAR(1),                -- 更新标识
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (ts_code, end_date),
    FOREIGN KEY (ts_code) REFERENCES stock_basic(ts_code)
);

CREATE INDEX idx_fina_end_date ON fina_indicator(end_date);
CREATE INDEX idx_fina_ann_date ON fina_indicator(ann_date);
```

**3. 资产负债表 (balancesheet)**

```sql
CREATE TABLE balancesheet (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    end_date DATE NOT NULL,
    ann_date DATE,
    
    -- 资产
    total_assets DECIMAL(20,2),            -- 资产总计
    total_cur_assets DECIMAL(20,2),        -- 流动资产合计
    total_nca DECIMAL(20,2),               -- 非流动资产合计
    
    -- 流动资产明细
    money_cap DECIMAL(20,2),               -- 货币资金
    trad_asset DECIMAL(20,2),              -- 交易性金融资产
    accounts_receiv DECIMAL(20,2),         -- 应收账款
    inventories DECIMAL(20,2),             -- 存货
    
    -- 非流动资产明细
    fix_assets DECIMAL(20,2),              -- 固定资产
    intan_assets DECIMAL(20,2),            -- 无形资产
    goodwill DECIMAL(20,2),                -- 商誉
    lt_eqt_invest DECIMAL(20,2),           -- 长期股权投资
    
    -- 负债
    total_liab DECIMAL(20,2),              -- 负债合计
    total_cur_liab DECIMAL(20,2),          -- 流动负债合计
    total_ncl DECIMAL(20,2),               -- 非流动负债合计
    
    -- 流动负债明细
    st_borr DECIMAL(20,2),                 -- 短期借款
    accounts_payable DECIMAL(20,2),        -- 应付账款
    
    -- 非流动负债明细
    lt_borr DECIMAL(20,2),                 -- 长期借款
    bond_payable DECIMAL(20,2),            -- 应付债券
    
    -- 所有者权益
    total_hldr_eqy_inc_min_int DECIMAL(20,2),  -- 股东权益合计
    cap_rese DECIMAL(20,2),                -- 资本公积
    undistr_porfit DECIMAL(20,2),          -- 未分配利润
    
    update_flag VARCHAR(1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (ts_code, end_date),
    FOREIGN KEY (ts_code) REFERENCES stock_basic(ts_code)
);

CREATE INDEX idx_balance_end_date ON balancesheet(end_date);
```

**4. 利润表 (income)**

```sql
CREATE TABLE income (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    end_date DATE NOT NULL,
    ann_date DATE,
    
    -- 收入
    total_revenue DECIMAL(20,2),           -- 营业总收入
    revenue DECIMAL(20,2),                 -- 营业收入
    
    -- 成本费用
    total_cogs DECIMAL(20,2),              -- 营业总成本
    oper_cost DECIMAL(20,2),               -- 营业成本
    sell_exp DECIMAL(20,2),                -- 销售费用
    admin_exp DECIMAL(20,2),               -- 管理费用
    fin_exp DECIMAL(20,2),                 -- 财务费用
    rd_exp DECIMAL(20,2),                  -- 研发费用
    
    -- 利润
    operate_profit DECIMAL(20,2),          -- 营业利润
    total_profit DECIMAL(20,2),            -- 利润总额
    income_tax DECIMAL(20,2),              -- 所得税费用
    n_income DECIMAL(20,2),                -- 净利润
    n_income_attr_p DECIMAL(20,2),         -- 归属于母公司净利润
    
    -- 其他
    invest_income DECIMAL(20,2),           -- 投资收益
    ebit DECIMAL(20,2),                    -- 息税前利润
    ebitda DECIMAL(20,2),                  -- 息税折旧摊销前利润
    
    update_flag VARCHAR(1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (ts_code, end_date),
    FOREIGN KEY (ts_code) REFERENCES stock_basic(ts_code)
);

CREATE INDEX idx_income_end_date ON income(end_date);
```

**5. 现金流量表 (cashflow)**

```sql
CREATE TABLE cashflow (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    end_date DATE NOT NULL,
    ann_date DATE,
    
    -- 经营活动现金流
    n_cashflow_act DECIMAL(20,2),          -- 经营活动现金流量净额
    c_fr_sale_sg DECIMAL(20,2),            -- 销售商品收到的现金
    c_paid_goods_s DECIMAL(20,2),          -- 购买商品支付的现金
    c_paid_to_for_empl DECIMAL(20,2),      -- 支付给职工的现金
    c_paid_for_taxes DECIMAL(20,2),        -- 支付的税费
    
    -- 投资活动现金流
    n_cashflow_inv_act DECIMAL(20,2),      -- 投资活动现金流量净额
    c_pay_acq_const_fiolta DECIMAL(20,2),  -- 购建固定资产支付的现金
    c_paid_invest DECIMAL(20,2),           -- 投资支付的现金
    
    -- 筹资活动现金流
    n_cash_flows_fnc_act DECIMAL(20,2),    -- 筹资活动现金流量净额
    c_recp_borrow DECIMAL(20,2),           -- 取得借款收到的现金
    c_prepay_amt_borr DECIMAL(20,2),       -- 偿还债务支付的现金
    
    -- 现金净增加额
    n_incr_cash_cash_equ DECIMAL(20,2),    -- 现金及现金等价物净增加额
    c_cash_equ_end_period DECIMAL(20,2),   -- 期末现金及现金等价物余额
    
    update_flag VARCHAR(1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (ts_code, end_date),
    FOREIGN KEY (ts_code) REFERENCES stock_basic(ts_code)
);

CREATE INDEX idx_cashflow_end_date ON cashflow(end_date);
```

**6. 重构报表表 (restructured_statements)**

```sql
CREATE TABLE restructured_statements (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    end_date DATE NOT NULL,
    statement_type VARCHAR(20) NOT NULL,   -- balance/income/cashflow
    item_name VARCHAR(100) NOT NULL,       -- 项目名称
    item_value DECIMAL(20,2),              -- 项目值
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date_type_item (ts_code, end_date, statement_type, item_name),
    FOREIGN KEY (ts_code) REFERENCES stock_basic(ts_code)
);

CREATE INDEX idx_restructured_type ON restructured_statements(statement_type);
CREATE INDEX idx_restructured_date ON restructured_statements(end_date);
```

**7. 核心指标计算表 (core_indicators_calculated)**

```sql
CREATE TABLE core_indicators_calculated (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    end_date DATE NOT NULL,
    
    -- ROIC相关
    roic DECIMAL(10,4),                        -- 投资资本回报率
    nopat DECIMAL(20,2),                       -- 息前税后经营利润
    invested_capital DECIMAL(20,2),            -- 投资资本
    
    -- 股权价值增加
    equity_value_added DECIMAL(20,2),          -- 股权价值增加值
    equity_cost DECIMAL(20,2),                 -- 股权资本成本
    
    -- 自由现金流
    operating_fcf DECIMAL(20,2),               -- 经营资产自由现金流
    expansion_capex DECIMAL(20,2),             -- 扩张性资本支出
    
    -- 资产结构
    financial_assets DECIMAL(20,2),            -- 金融资产合计
    operating_assets DECIMAL(20,2),            -- 经营资产合计
    lt_equity_invest DECIMAL(20,2),            -- 长期股权投资
    
    -- 负债结构
    interest_bearing_debt DECIMAL(20,2),       -- 有息债务合计
    non_interest_bearing_liab DECIMAL(20,2),   -- 无息负债合计
    
    -- 利润率指标
    gross_margin DECIMAL(10,4),                -- 毛利率
    operating_margin DECIMAL(10,4),            -- 营业利润率
    net_margin DECIMAL(10,4),                  -- 净利率
    
    -- 费用率指标
    selling_expense_ratio DECIMAL(10,4),       -- 销售费用率
    admin_expense_ratio DECIMAL(10,4),         -- 管理费用率
    rd_expense_ratio DECIMAL(10,4),            -- 研发费用率
    
    -- 周转率指标
    total_asset_turnover DECIMAL(10,4),        -- 总资产周转率
    operating_asset_turnover DECIMAL(10,4),    -- 经营资产周转率
    
    -- 杠杆指标
    debt_to_asset_ratio DECIMAL(10,4),         -- 资产负债率
    debt_to_equity_ratio DECIMAL(10,4),        -- 产权比率
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_code_date (ts_code, end_date),
    FOREIGN KEY (ts_code) REFERENCES stock_basic(ts_code)
);

CREATE INDEX idx_core_end_date ON core_indicators_calculated(end_date);
CREATE INDEX idx_core_roic ON core_indicators_calculated(roic);
```

**8. 数据更新日志表 (data_update_log)**

```sql
CREATE TABLE data_update_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(20),                   -- 股票代码（NULL表示全量更新）
    update_type VARCHAR(20) NOT NULL,      -- 更新类型：full/incremental
    data_type VARCHAR(50),                 -- 数据类型：basic/fina/balance/income/cashflow/all
    start_date DATE,                       -- 更新开始日期
    end_date DATE,                         -- 更新结束日期
    status VARCHAR(20),                    -- 状态：success/failed/running
    records_updated INT,                   -- 更新记录数
    error_message TEXT,                    -- 错误信息
    started_at TIMESTAMP,                  -- 开始时间
    completed_at TIMESTAMP,                -- 完成时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_log_ts_code ON data_update_log(ts_code);
CREATE INDEX idx_log_update_type ON data_update_log(update_type);
CREATE INDEX idx_log_created_at ON data_update_log(created_at);
```

### 数据库操作实现

#### 1. 数据库连接管理

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import yaml

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config_path='config.yaml'):
        """初始化数据库连接"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        db_config = config['data']['database']
        self.db_type = db_config['type']
        
        # 构建连接字符串
        if self.db_type == 'sqlite':
            self.connection_string = f"sqlite:///{db_config.get('path', 'stock_data.db')}"
        elif self.db_type == 'mysql':
            self.connection_string = (
                f"mysql+pymysql://{db_config['username']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
                f"?charset=utf8mb4"
            )
        elif self.db_type == 'postgresql':
            self.connection_string = (
                f"postgresql://{db_config['username']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            )
        
        self.engine = create_engine(self.connection_string, echo=False)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """获取数据库会话"""
        return self.Session()
    
    def execute_query(self, query):
        """执行查询"""
        with self.engine.connect() as conn:
            return conn.execute(query)
```

#### 2. 数据插入/更新

```python
def save_to_database(self, df, table_name, ts_code, if_exists='append'):
    """
    保存数据到数据库
    
    Args:
        df: DataFrame数据
        table_name: 表名
        ts_code: 股票代码
        if_exists: 'append'追加, 'replace'替换
    """
    db_manager = DatabaseManager()
    
    # 添加股票代码列（如果不存在）
    if 'ts_code' not in df.columns:
        df['ts_code'] = ts_code
    
    # 添加时间戳
    df['updated_at'] = datetime.now()
    
    # 保存到数据库
    df.to_sql(
        table_name,
        db_manager.engine,
        if_exists=if_exists,
        index=False,
        method='multi',
        chunksize=1000
    )
    
    logger.info(f"已保存 {len(df)} 条记录到 {table_name}")
```

#### 3. 增量更新逻辑

```python
def incremental_update(self, ts_code, days_back=90):
    """
    增量更新：只更新最近N天的数据
    
    Args:
        ts_code: 股票代码
        days_back: 回溯天数
    """
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    try:
        # 1. 查询最后更新日期
        last_update = session.query(
            func.max(FinaIndicator.end_date)
        ).filter(
            FinaIndicator.ts_code == ts_code
        ).scalar()
        
        # 2. 确定更新起始日期
        if last_update:
            start_date = (last_update - timedelta(days=days_back)).strftime('%Y%m%d')
        else:
            # 如果没有历史数据，获取全部
            start_date = None
        
        end_date = datetime.now().strftime('%Y%m%d')
        
        # 3. 获取新数据
        logger.info(f"增量更新 {ts_code}: {start_date} -> {end_date}")
        data = self.get_all_financial_data(ts_code, start_date, end_date)
        
        # 4. 更新到数据库（使用UPSERT）
        for table_name, df in data.items():
            if df is not None and len(df) > 0:
                self._upsert_data(df, table_name, ts_code)
        
        # 5. 记录更新日志
        self._log_update(ts_code, 'incremental', 'all', start_date, end_date, 'success')
        
        session.commit()
        logger.info(f"增量更新完成: {ts_code}")
        
    except Exception as e:
        session.rollback()
        self._log_update(ts_code, 'incremental', 'all', start_date, end_date, 'failed', str(e))
        logger.error(f"增量更新失败: {ts_code}, {e}")
        raise
    finally:
        session.close()

def _upsert_data(self, df, table_name, ts_code):
    """
    UPSERT操作：存在则更新，不存在则插入
    """
    db_manager = DatabaseManager()
    
    if db_manager.db_type == 'mysql':
        # MySQL使用ON DUPLICATE KEY UPDATE
        df.to_sql(
            table_name,
            db_manager.engine,
            if_exists='append',
            index=False,
            method='multi'
        )
    elif db_manager.db_type == 'postgresql':
        # PostgreSQL使用ON CONFLICT DO UPDATE
        # 实现类似逻辑
        pass
    else:
        # SQLite使用REPLACE
        df.to_sql(
            table_name,
            db_manager.engine,
            if_exists='replace',
            index=False
        )
```

#### 4. 全量更新逻辑

```python
def full_update(self, ts_code):
    """
    全量更新：获取并更新所有历史数据
    
    Args:
        ts_code: 股票代码
    """
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    try:
        logger.info(f"开始全量更新: {ts_code}")
        
        # 1. 获取全部历史数据
        data = self.get_all_financial_data(ts_code, start_date=None, end_date=None)
        
        # 2. 清空旧数据
        for table_name in ['fina_indicator', 'balancesheet', 'income', 'cashflow']:
            session.query(eval(table_name.capitalize())).filter_by(ts_code=ts_code).delete()
        
        # 3. 插入新数据
        for table_name, df in data.items():
            if df is not None and len(df) > 0:
                self.save_to_database(df, table_name, ts_code, if_exists='append')
        
        # 4. 记录更新日志
        self._log_update(ts_code, 'full', 'all', None, None, 'success')
        
        session.commit()
        logger.info(f"全量更新完成: {ts_code}")
        
    except Exception as e:
        session.rollback()
        self._log_update(ts_code, 'full', 'all', None, None, 'failed', str(e))
        logger.error(f"全量更新失败: {ts_code}, {e}")
        raise
    finally:
        session.close()
```

### 数据库配置

在 `config.yaml` 中添加数据库配置：

```yaml
data:
  output_dir: "./data"
  save_csv: true
  save_excel: false
  save_database: true              # 是否保存到数据库
  
  database:
    type: "mysql"                  # sqlite/mysql/postgresql
    host: "localhost"
    port: 3306
    username: "stock_user"
    password: "your_password"
    database: "stock_finance"
    
    # SQLite配置（如果使用SQLite）
    path: "./data/stock_data.db"
    
    # 连接池配置
    pool_size: 10
    max_overflow: 20
    pool_recycle: 3600
```

### 数据查询示例

```python
# 查询某只股票的最新财务指标
def get_latest_indicators(ts_code):
    """获取最新财务指标"""
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    result = session.query(FinaIndicator).filter(
        FinaIndicator.ts_code == ts_code
    ).order_by(
        FinaIndicator.end_date.desc()
    ).first()
    
    session.close()
    return result

# 查询某个行业的平均ROIC
def get_industry_avg_roic(industry, end_date):
    """获取行业平均ROIC"""
    db_manager = DatabaseManager()
    
    query = f"""
    SELECT AVG(fi.roic) as avg_roic
    FROM fina_indicator fi
    JOIN stock_basic sb ON fi.ts_code = sb.ts_code
    WHERE sb.industry = '{industry}'
    AND fi.end_date = '{end_date}'
    """
    
    result = db_manager.execute_query(query)
    return result.fetchone()[0]

# 查询多期数据对比
def get_multi_period_data(ts_code, start_date, end_date):
    """获取多期数据"""
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    
    results = session.query(FinaIndicator).filter(
        FinaIndicator.ts_code == ts_code,
        FinaIndicator.end_date >= start_date,
        FinaIndicator.end_date <= end_date
    ).order_by(
        FinaIndicator.end_date
    ).all()
    
    session.close()
    return results
```

---

## 配置说明

### config.yaml配置文件

```yaml
# Tushare API配置
tushare:
  token: "YOUR_TOKEN"           # Tushare API Token
  api:
    request_interval: 0.3       # 请求间隔（秒）
    page_size: 5000             # 分页大小
    max_retries: 3              # 最大重试次数
    retry_interval: 1           # 重试间隔（秒）

# 数据存储配置
data:
  output_dir: "./data"          # 输出目录
  save_csv: true                # 保存CSV
  save_excel: false             # 保存Excel

# 日志配置
logging:
  level: "INFO"                 # 日志级别
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "./logs/tushare_client.log"

# 财务报表重构配置
restructure:
  equity_cost_rate: 0.08        # 股权资本成本率（8%）
```

---

## 扩展开发指南

### 添加新的财务指标

**步骤1**: 在重构模块中添加计算逻辑

```python
# 在 income_statement_restructure.py 中添加
def calculate_custom_indicator(df_data, date_columns):
    """计算自定义指标"""
    # 获取所需数据
    revenue = _safe_get_value(df_data, '营业收入', date_columns)
    cost = _safe_get_value(df_data, '营业成本', date_columns)
    
    # 计算指标
    custom_ratio = (revenue - cost) / revenue
    
    return custom_ratio
```

**步骤2**: 在输出顺序中添加

```python
output_order = [
    # ... 现有指标
    '自定义指标',
    # ...
]
```

**步骤3**: 在报告生成器中添加图表

```python
# 在 html_report_generator.py 中添加
def generate_custom_chart(self, df):
    """生成自定义指标图表"""
    # 实现图表生成逻辑
    pass
```

---

### 添加新的数据源

**步骤1**: 创建新的客户端类

```python
class CustomDataClient:
    """自定义数据源客户端"""
    
    def __init__(self, config):
        self.config = config
    
    def get_data(self, symbol, start_date, end_date):
        """获取数据"""
        # 实现数据获取逻辑
        pass
```

**步骤2**: 在main.py中集成

```python
# 添加命令行参数
parser.add_argument('--data-source', choices=['tushare', 'custom'])

# 根据参数选择客户端
if args.data_source == 'custom':
    client = CustomDataClient(config)
else:
    client = TushareClient(config)
```

---

## 性能优化

### 1. 批量处理优化

使用`recalculate_all_ultra_optimized.py`进行批量处理：

```python
# 特性：
- 多进程并行处理
- 智能错误恢复
- 进度持久化
- 内存优化
```

### 2. 数据缓存

```python
# TushareClient内置缓存
- 股票上市日期缓存
- 避免重复API调用
```

### 3. API请求优化

```python
# 配置优化
tushare:
  api:
    request_interval: 0.3  # 根据积分等级调整
    page_size: 5000        # 大数据量时增加分页大小
```

---

## 故障排查

### 常见问题

**1. Token错误**

```
错误: 配置文件不存在: config.yaml
解决: 复制config.yaml.example为config.yaml并填入Token
```

**2. 积分不足**

```
错误: 部分接口返回空数据
解决: 检查Tushare积分，升级积分等级
```

**3. 数据为空**

```
原因:
- 股票代码错误
- 日期范围内无数据
- 积分不足
解决: 检查股票代码格式，扩大日期范围
```

**4. 内存不足**

```
错误: MemoryError
解决: 
- 减少批量处理的股票数量
- 使用--years参数限制年数
- 增加系统内存
```

### 调试技巧

**1. 启用DEBUG日志**

```yaml
# config.yaml
logging:
  level: "DEBUG"
```

**2. 单步测试**

```python
# 测试单个模块
from balance_sheet_restructure import restructure_balance_sheet

df = pd.read_csv('test_data.csv')
result = restructure_balance_sheet(df)
print(result)
```

**3. 数据验证**

```python
# 检查数据完整性
print(f"数据形状: {df.shape}")
print(f"空值统计:\n{df.isnull().sum()}")
print(f"数据类型:\n{df.dtypes}")
```

---

## 版本历史

- **v2.0** (2025-03): 完整重构版本，支持年报+TTM
- **v1.5** (2024-12): 添加HTML报告生成
- **v1.0** (2024-06): 初始版本

---

## 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

---

## 许可证

MIT License

---

## 联系方式

项目维护者: [您的联系方式]
项目地址: [GitHub链接]
