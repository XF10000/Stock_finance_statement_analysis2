# 项目结构说明

## 完整目录结构

```
Stock_finance_statement_analysis2/
│
├── main.py                                    # 主程序入口
├── requirements.txt                           # Python依赖包列表
├── config.yaml.example                        # 配置文件模板
├── README.md                                  # 项目说明文档
├── 快速开始.md                                # 快速开始指南
│
├── docs/                                      # 文档目录
│   ├── TECHNICAL_DOCUMENTATION.md             # 技术文档（开发者）
│   ├── USER_GUIDE.md                          # 用户使用手册
│   ├── PROJECT_STRUCTURE.md                   # 项目结构说明（本文件）
│   ├── Annual_TTM_Guide.md                    # 年报+TTM说明
│   ├── 000333_Detailed_Analysis_Report.md     # 示例分析报告
│   ├── 000333_Test_Report.md                  # 测试报告
│   ├── 600900_Test_Report.md                  # 测试报告
│   ├── 参考/                                  # 参考资料
│   └── 图表汇总/                              # 图表汇总
│       ├── 01_资产负债分析/
│       ├── 02_利润分析/
│       └── 03_经营效率/
│
├── data/                                      # 数据输出目录
│   └── [股票代码]/                            # 按股票代码分类存储
│
├── test_results/                              # 测试结果目录
│
├── .git/                                      # Git版本控制
└── .gitignore                                 # Git忽略文件配置
```

---

## 核心Python模块（17个）

### 1. 主程序模块

#### `main.py`
- **功能**: 主程序入口，命令行接口
- **依赖**: 所有核心模块
- **输入**: 命令行参数（股票代码、日期范围等）
- **输出**: 完整的财务分析报告
- **关键函数**:
  - `main()`: 主流程控制
  - `normalize_ts_code()`: 股票代码标准化
  - `get_total_share_data()`: 获取总股本数据
  - `add_total_share_to_balance()`: 添加总股本到资产负债表

---

### 2. 数据获取模块

#### `tushare_client.py`
- **功能**: Tushare API客户端，数据获取和基础处理
- **依赖**: `field_mapping.py`
- **核心类**: `TushareClient`
- **主要方法**:
  - `get_fina_indicator()`: 获取财务指标表
  - `get_balancesheet()`: 获取资产负债表
  - `get_income()`: 获取利润表
  - `get_cashflow()`: 获取现金流量表
  - `get_all_financial_data()`: 一次性获取所有数据
  - `transpose_data()`: 数据转置
  - `save_to_csv()`: 保存为CSV
  - `save_to_excel()`: 保存为Excel
- **特性**:
  - 自动分页处理
  - 错误重试机制
  - 数据过滤（上市前、更新版本）
  - 字段翻译
  - 请求限流

#### `field_mapping.py`
- **功能**: 财务字段中英文映射
- **包含映射**:
  - `FINA_INDICATOR_FIELDS`: 财务指标表（~180字段）
  - `BALANCESHEET_FIELDS`: 资产负债表（~156字段）
  - `INCOME_FIELDS`: 利润表（~94字段）
  - `CASHFLOW_FIELDS`: 现金流量表（~99字段）
- **核心函数**:
  - `translate_columns()`: 翻译DataFrame列名
  - `get_field_description()`: 获取字段描述

---

### 3. 财务报表重构模块

#### `balance_sheet_restructure.py`
- **功能**: 资产负债表重构（资产-资本结构）
- **核心函数**: `restructure_balance_sheet(df)`
- **重构内容**:
  - 金融资产合计
  - 长期股权投资
  - 经营资产合计（周转性 + 长期）
  - 有息债务合计（短期 + 长期）
  - 所有者权益合计
- **字段映射**: `UNIFIED_FIELD_MAPPING`
- **输出**: 重构后的资产负债表DataFrame

#### `income_statement_restructure.py`
- **功能**: 利润表重构（股权价值增加表）
- **核心函数**: `restructure_income_statement(df, equity_data, equity_cost_rate=0.08)`
- **重构内容**:
  - 营业收入与成本分析
  - 期间费用分析
  - 息税前经营利润
  - 息前税后经营利润
  - 投资收益分析
  - 金融资产收益分析
  - 股权价值增加值
- **字段映射**: `INCOME_FIELD_MAPPING`
- **参数**: `equity_cost_rate` 股权资本成本率（默认8%）

#### `cashflow_statement_restructure.py`
- **功能**: 现金流量表重构（自由现金流分析）
- **核心函数**: `restructure_cashflow_statement(df_cashflow, income_data, balance_data, income_restructured)`
- **重构内容**:
  - 自由现金流量分析
  - 经营资产自由现金流量
  - 长期经营资产投资分析
  - 资本支出分析（扩张性CAPEX）
  - 债务筹资分析
- **字段映射**: `CASHFLOW_FIELD_MAPPING`
- **依赖数据**: 原始现金流、利润表、资产负债表

---

### 4. 数据处理模块

#### `annual_report_generator.py`
- **功能**: 生成年报+TTM数据
- **核心类**: `AnnualReportGenerator`
- **主要方法**:
  - `generate_annual_reports_with_ttm()`: 生成年报+TTM
  - `_generate_balance_sheet_annual_with_ttm()`: 资产负债表年报+TTM
  - `_generate_income_statement_annual_with_ttm()`: 利润表年报+TTM
  - `_generate_cashflow_statement_annual_with_ttm()`: 现金流量表年报+TTM
  - `_calculate_ttm()`: TTM计算
  - `format_annual_report()`: 格式化年报
- **TTM计算**: `TTM = 今年Q累计 - 去年同Q累计 + 去年Q4累计`
- **输出**: 包含年报和TTM的三大报表字典

---

### 5. 报告生成模块

#### `html_report_generator.py`
- **功能**: 生成HTML交互式财务分析报告
- **核心类**: `HTMLReportGenerator`
- **报告内容**:
  - 利润分析（收入、毛利率、净利率、费用率）
  - 资产负债分析（资产结构、负债结构、资产负债率）
  - 经营效率分析（ROIC、ROE、周转率）
- **技术**: ECharts图表库
- **输出**: HTML文件

#### `final_report_generator_echarts.py`
- **功能**: 生成核心指标分析报告（ECharts版本）
- **依赖**: `core_indicators_analyzer.py`
- **报告内容**:
  - 盈利能力指标
  - 成长性指标
  - 偿债能力指标
  - 营运能力指标
  - 核心指标趋势图
- **输出**: HTML文件

#### `fcff_report_generator.py`
- **功能**: 生成FCFF（企业自由现金流）专项报告
- **核心类**: `FCFFReportGenerator`
- **报告内容**:
  - FCFF计算与分析
  - 现金流质量分析
  - 资本支出分析
- **输出**: HTML文件

#### `summary_excel_generator.py`
- **功能**: 生成Excel汇总报告
- **核心类**: `SummaryExcelGenerator`
- **报告内容**:
  - 多期财务数据汇总
  - 关键指标对比
  - 趋势分析
- **输出**: Excel文件

---

### 6. 分析模块

#### `core_indicators_analyzer.py`
- **功能**: 核心财务指标计算与分析
- **核心类**: `CoreIndicatorsAnalyzer`
- **计算指标**:
  - ROIC（投资资本回报率）
  - ROE（净资产收益率）
  - 毛利率、净利率
  - 资产负债率
  - 流动比率、速动比率
  - 周转率指标
  - 增长率指标
- **输出**: 指标DataFrame

#### `financial_data_analyzer.py`
- **功能**: 市场数据分析
- **核心类**: `FinancialDataAnalyzer`
- **分析内容**:
  - 市场估值分析
  - 行业对比分析
  - 市场表现分析
- **依赖**: 市场数据

#### `financial_data_manager.py`
- **功能**: 市场数据管理
- **核心类**: `FinancialDataManager`
- **功能**:
  - 市场数据获取
  - 数据缓存管理
  - 数据更新
- **输出**: 市场数据DataFrame

---

### 7. 工具模块

#### `update_financial_data.py`
- **功能**: 财务数据更新工具
- **用途**: 定期更新市场数据
- **运行方式**: 独立脚本

#### `recalculate_all_ultra_optimized.py`
- **功能**: 批量计算所有A股数据（超级优化版）
- **特性**:
  - 多进程并行处理
  - 智能错误恢复
  - 进度持久化
  - 内存优化
- **用途**: 批量处理大量股票数据
- **运行方式**: 独立脚本

#### `fetch_all_a_shares_safe.py`
- **功能**: 安全获取所有A股数据
- **特性**:
  - 错误处理
  - 进度保存
  - 断点续传
- **用途**: 批量获取A股基础数据
- **运行方式**: 独立脚本

---

## 配置文件

### `config.yaml`（需从config.yaml.example创建）

```yaml
# Tushare API配置
tushare:
  token: "YOUR_TOKEN"              # 必填：Tushare API Token
  api:
    request_interval: 0.3          # API请求间隔（秒）
    page_size: 5000                # 分页大小
    max_retries: 3                 # 最大重试次数
    retry_interval: 1              # 重试间隔（秒）

# 数据存储配置
data:
  output_dir: "./data"             # 数据输出目录
  save_csv: true                   # 是否保存CSV
  save_excel: false                # 是否保存Excel

# 日志配置
logging:
  level: "INFO"                    # 日志级别
  file: "./logs/tushare_client.log"

# 财务报表重构配置
restructure:
  equity_cost_rate: 0.08           # 股权资本成本率（8%）
```

---

## 数据流向图

```
┌─────────────────┐
│  命令行输入      │
│  python main.py │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  TushareClient                  │
│  - 获取财务指标表                │
│  - 获取资产负债表                │
│  - 获取利润表                    │
│  - 获取现金流量表                │
│  - 字段翻译                      │
│  - 数据转置                      │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  财务报表重构                    │
│  - balance_sheet_restructure    │
│  - income_statement_restructure │
│  - cashflow_statement_restructure│
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  AnnualReportGenerator          │
│  - 生成年报数据                  │
│  - 计算TTM数据                   │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  报告生成                        │
│  - HTML财务分析报告              │
│  - 核心指标报告                  │
│  - FCFF专项报告                  │
│  - Excel汇总报告                 │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  输出文件                        │
│  - CSV数据文件                   │
│  - Excel文件                     │
│  - HTML报告                      │
└─────────────────────────────────┘
```

---

## 模块依赖关系

```
main.py
├── tushare_client.py
│   └── field_mapping.py
├── balance_sheet_restructure.py
├── income_statement_restructure.py
├── cashflow_statement_restructure.py
│   ├── income_statement_restructure.py
│   └── balance_sheet_restructure.py
├── annual_report_generator.py
├── html_report_generator.py
├── final_report_generator_echarts.py
│   └── core_indicators_analyzer.py
├── fcff_report_generator.py
└── summary_excel_generator.py

独立工具脚本：
├── update_financial_data.py
│   └── financial_data_manager.py
├── recalculate_all_ultra_optimized.py
│   └── main.py (调用主程序逻辑)
└── fetch_all_a_shares_safe.py
    └── tushare_client.py
```

---

## 输出文件说明

### 单只股票分析输出（以000333.SZ为例）

```
data/
└── 000333.SZ/
    ├── 原始数据文件：
    │   ├── 000333.SZ_fina_indicator.csv          # 财务指标表
    │   ├── 000333.SZ_balancesheet.csv            # 原始资产负债表
    │   ├── 000333.SZ_income.csv                  # 原始利润表
    │   └── 000333.SZ_cashflow.csv                # 原始现金流量表
    │
    ├── 重构数据文件：
    │   ├── 000333.SZ_balancesheet_restructured.csv    # 重构资产负债表
    │   ├── 000333.SZ_income_restructured.csv          # 重构利润表
    │   └── 000333.SZ_cashflow_restructured.csv        # 重构现金流量表
    │
    ├── 年报+TTM文件：
    │   ├── 000333.SZ_balance_sheet_annual_ttm.csv     # 年报+TTM资产负债表
    │   ├── 000333.SZ_income_statement_annual_ttm.csv  # 年报+TTM利润表
    │   └── 000333.SZ_cashflow_statement_annual_ttm.csv # 年报+TTM现金流量表
    │
    ├── 分析报告：
    │   ├── 000333.SZ_financial_report.html            # HTML财务分析报告
    │   ├── 000333.SZ_核心指标_20250316_152030.html    # 核心指标报告
    │   └── 000333.SZ_fcff_report.html                 # FCFF专项报告
    │
    └── 其他数据：
        └── 000333.SZ_分红送股.xlsx                    # 分红送股数据
```

---

## 开发规范

### 代码风格

- **Python版本**: 3.8+
- **编码规范**: PEP 8
- **文档字符串**: Google风格
- **类型提示**: 推荐使用

### 命名规范

- **文件名**: 小写字母+下划线（snake_case）
- **类名**: 大驼峰（PascalCase）
- **函数名**: 小写字母+下划线（snake_case）
- **常量**: 全大写+下划线（UPPER_CASE）

### 文档规范

- **模块文档**: 每个模块顶部包含功能说明
- **函数文档**: 包含参数、返回值、示例
- **注释**: 关键逻辑添加注释

---

## 扩展指南

### 添加新的财务指标

1. 在对应的重构模块中添加计算逻辑
2. 更新输出顺序列表
3. 在报告生成器中添加图表展示
4. 更新文档说明

### 添加新的报告类型

1. 创建新的报告生成器类
2. 继承或参考现有报告生成器
3. 在main.py中集成调用
4. 添加命令行参数（如需要）

### 添加新的数据源

1. 创建新的数据客户端类
2. 实现统一的数据接口
3. 在main.py中添加数据源选择逻辑
4. 更新配置文件

---

## 版本控制

### Git工作流

```bash
# 克隆项目
git clone [项目地址]

# 创建功能分支
git checkout -b feature/new-feature

# 提交更改
git add .
git commit -m "Add new feature"

# 推送到远程
git push origin feature/new-feature

# 创建Pull Request
```

### 版本号规范

- **主版本号**: 重大架构变更
- **次版本号**: 新功能添加
- **修订号**: Bug修复

当前版本: v2.0

---

## 性能考虑

### 内存优化

- 使用迭代器处理大数据集
- 及时释放不需要的DataFrame
- 批量处理时控制并发数

### 速度优化

- 使用多进程并行处理
- 缓存常用数据（如上市日期）
- 减少不必要的API调用

### 存储优化

- 定期清理临时文件
- 压缩历史数据
- 使用数据库存储（可选）

---

## 安全考虑

### API密钥安全

- Token存储在config.yaml（已加入.gitignore）
- 不要将Token提交到版本控制
- 定期更换Token

### 数据安全

- 本地存储，不上传云端
- 定期备份重要数据
- 注意数据使用合规性

---

## 测试

### 单元测试

```bash
# 运行测试（如有）
python -m pytest tests/
```

### 集成测试

```bash
# 测试完整流程
python main.py 000333 --years 1
```

### 性能测试

```bash
# 测试批量处理性能
time python recalculate_all_ultra_optimized.py
```

---

## 常见问题

详见 `docs/USER_GUIDE.md` 的常见问题章节。

---

**文档版本**: v1.0  
**最后更新**: 2025-03-16
