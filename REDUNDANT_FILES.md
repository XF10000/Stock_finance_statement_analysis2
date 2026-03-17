# 冗余文件清单

## 需要删除的文件

基于项目分析，以下文件为冗余或过时版本，建议删除：

### 1. 重复的批量计算脚本（保留最优化版本）

**删除原因**：这些是同一功能的不同迭代版本，应只保留最优化版本

- `calculate_all_indicators.py` - 早期版本
- `calculate_all_indicators_optimized.py` - 中期优化版本
- `recalculate_all_batch.py` - 批量计算早期版本
- `recalculate_all_simple.py` - 简化版本
- `recalculate_all_distributions_optimized.py` - 中期优化版本

**保留**：`recalculate_all_ultra_optimized.py` - 最终超级优化版本

### 2. 重复的数据获取脚本

**删除原因**：功能重复，保留更安全的版本

- `fetch_all_a_shares.py` - 早期版本

**保留**：`fetch_all_a_shares_safe.py` - 更安全的版本

### 3. 测试/临时脚本

**删除原因**：这些是特定用途的临时脚本，不属于核心功能

- `calculate_100_indicators.py` - 仅用于100只股票的测试脚本
- `fetch_100_stocks.py` - 仅用于获取100只股票的测试脚本
- `recalculate_2025q3_distribution.py` - 特定季度的临时脚本
- `recalculate_single_stock.py` - 单股票测试脚本

### 4. 过时的报告生成器

**删除原因**：已被更新版本替代

- `enhanced_report_generator.py` - 早期增强版本
- `stock_report_generator.py` - 早期股票报告生成器

**保留**：
- `html_report_generator.py` - HTML报告生成器（用于财务分析）
- `final_report_generator_echarts.py` - 核心指标报告生成器（最终版本）
- `fcff_report_generator.py` - FCFF专项报告生成器
- `summary_excel_generator.py` - Excel汇总生成器

### 5. 其他工具脚本

**删除原因**：功能已整合到主程序或不再使用

- `generate_report.py` - 功能已整合到main.py

## 删除命令

```bash
# 在项目根目录执行以下命令删除冗余文件

# 删除重复的批量计算脚本
rm calculate_all_indicators.py
rm calculate_all_indicators_optimized.py
rm recalculate_all_batch.py
rm recalculate_all_simple.py
rm recalculate_all_distributions_optimized.py

# 删除重复的数据获取脚本
rm fetch_all_a_shares.py

# 删除测试/临时脚本
rm calculate_100_indicators.py
rm fetch_100_stocks.py
rm recalculate_2025q3_distribution.py
rm recalculate_single_stock.py

# 删除过时的报告生成器
rm enhanced_report_generator.py
rm stock_report_generator.py

# 删除其他工具脚本
rm generate_report.py
```

## 核心保留文件（15个Python文件）

1. **main.py** - 主程序入口
2. **tushare_client.py** - Tushare API客户端
3. **field_mapping.py** - 字段中英文映射
4. **balance_sheet_restructure.py** - 资产负债表重构
5. **income_statement_restructure.py** - 利润表重构
6. **cashflow_statement_restructure.py** - 现金流量表重构
7. **annual_report_generator.py** - 年报+TTM生成器
8. **html_report_generator.py** - HTML财务分析报告
9. **final_report_generator_echarts.py** - 核心指标报告（ECharts）
10. **fcff_report_generator.py** - FCFF专项报告
11. **summary_excel_generator.py** - Excel汇总生成器
12. **core_indicators_analyzer.py** - 核心指标分析器
13. **financial_data_analyzer.py** - 市场分析器
14. **financial_data_manager.py** - 财务数据管理器
15. **update_financial_data.py** - 财务数据更新工具
16. **recalculate_all_ultra_optimized.py** - 批量计算最优化版本
17. **fetch_all_a_shares_safe.py** - 安全的A股数据获取

## 删除后的项目结构

```
Stock_finance_statement_analysis2/
├── main.py                                    # 主程序入口
├── tushare_client.py                          # API客户端
├── field_mapping.py                           # 字段映射
├── balance_sheet_restructure.py               # 资产负债表重构
├── income_statement_restructure.py            # 利润表重构
├── cashflow_statement_restructure.py          # 现金流量表重构
├── annual_report_generator.py                 # 年报+TTM生成
├── html_report_generator.py                   # HTML报告
├── final_report_generator_echarts.py          # 核心指标报告
├── fcff_report_generator.py                   # FCFF报告
├── summary_excel_generator.py                 # Excel汇总
├── core_indicators_analyzer.py                # 核心指标分析
├── financial_data_analyzer.py                         # 市场分析
├── financial_data_manager.py                     # 市场数据管理
├── update_financial_data.py                      # 数据更新
├── recalculate_all_ultra_optimized.py         # 批量计算
├── fetch_all_a_shares_safe.py                 # A股数据获取
├── config.yaml.example                        # 配置模板
├── requirements.txt                           # 依赖包
├── README.md                                  # 项目说明
├── 快速开始.md                                # 快速开始
├── data/                                      # 数据目录
├── docs/                                      # 文档目录
└── test_results/                              # 测试结果
```
