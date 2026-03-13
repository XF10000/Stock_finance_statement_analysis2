# 资产负债表重构指南

## 概述

本模块将传统资产负债表重构为"资产-资本"结构，便于分析企业的金融资产、经营资产、有息债务和所有者权益。

## 重构原理

### 传统资产负债表 vs 重构后的资产负债表

**传统结构**：
```
资产 = 负债 + 所有者权益
```

**重构后结构**：
```
资产结构：
  - 金融资产合计
  - 长期股权投资
  - 经营资产合计
    - 周转性经营投入合计
    - 长期经营资产合计

资本结构：
  - 有息债务合计
  - 所有者权益合计
```

### 核心区别

1. **金融资产 vs 经营资产**
   - 金融资产：企业持有的金融工具（货币资金、交易性金融资产、债权投资等）
   - 经营资产：用于日常经营活动的资产（应收账款、存货、固定资产等）

2. **营运资产 vs 营运负债**
   - 营运资产：经营性流动资产（应收、存货等）
   - 营运负债：经营性流动负债（应付、预收等）
   - 周转性经营投入 = 营运资产 - 营运负债（反映了企业的营运资金占用）

3. **有息债务 vs 无息负债**
   - 有息债务：需要支付利息的债务（银行借款、债券等）
   - 无息负债：不需要支付利息的负债（应付账款、预收款项等经营性负债）

## 使用方法

### 1. 基本使用

```python
import pandas as pd
from balance_sheet_restructure import restructure_balance_sheet

# 读取资产负债表数据（转置格式）
df = pd.read_csv('data/603345.SH_balancesheet.csv', encoding='utf-8-sig')

# 重构资产负债表
df_restructured = restructure_balance_sheet(df)

# 保存结果
df_restructured.to_csv('data/603345.SH_balancesheet_restructured.csv', 
                       index=False, encoding='utf-8-sig')
```

### 2. 与TushareClient集成

```python
from tushare_client import TushareClient
from balance_sheet_restructure import restructure_balance_sheet

# 初始化客户端
client = TushareClient()

# 获取原始资产负债表
balancesheet = client.get_balancesheet('603345.SH', translate=True)

# 重构资产负债表
balancesheet_restructured = restructure_balance_sheet(balancesheet)

# 保存
client.save_to_csv({'balancesheet_restructured': balancesheet_restructured}, 
                   '603345.SH')
```

## 字段说明

### 资产结构字段

| 项目 | 说明 | 包含科目 |
|------|------|----------|
| 金融资产合计 | 企业持有的金融工具 | 货币资金、交易性金融资产、债权投资、投资性房地产等 |
| 长期股权投资 | 对外股权投资 | 长期股权投资、其他权益工具投资 |
| 经营资产合计 | 用于经营活动的资产 | 周转性经营投入 + 长期经营资产 |
| 周转性经营投入合计 | 营运资金占用 | 营运资产小计 - 营运负债小计 |
| 营运资产小计 | 经营性流动资产 | 应收票据、应收账款、存货、预付款项等 |
| 营运负债小计 | 经营性流动负债 | 应付票据、应付账款、预收款项、合同负债等 |
| 长期经营资产合计 | 经营性长期资产 | 固定资产、无形资产、在建工程等 |

### 资本结构字段

| 项目 | 说明 | 包含科目 |
|------|------|----------|
| 有息债务合计 | 需付息的债务 | 短期债务 + 长期债务 |
| 短期债务 | 短期有息负债 | 短期借款、一年内到期的非流动负债等 |
| 长期债务 | 长期有息负债 | 长期借款、应付债券、租赁负债等 |
| 所有者权益合计 | 股东权益 | 归属母公司股东权益 + 少数股东权益 |

### 特殊调整项

1. **其他应收款调整**
   ```
   其他应收款(调整后) = 其他应收款 - 应收利息 - 应收股利
   ```
   - 应收利息和应收股利属于金融资产，需要从其他应收款中扣除

2. **其他应付款调整**
   ```
   其他应付款(调整后) = 其他应付款 - 应付利息 - 应付股利
   ```
   - 应付利息属于有息债务，需要从其他应付款中扣除

3. **递延所得税负债处理**
   ```
   长期经营资产合计 = ... + 递延所得税资产 - 递延所得税负债
   ```
   - 递延所得税负债作为减项，因为它本质上是负债而非资产

## 分析应用

### 1. 企业资产结构分析

```python
# 计算各资产占比
total_assets = df_restructured[df_restructured['项目'] == '资产总额'][date].values[0]
financial_assets = df_restructured[df_restructured['项目'] == '金融资产合计'][date].values[0]
operating_assets = df_restructured[df_restructured['项目'] == '经营资产合计'][date].values[0]

print(f"金融资产占比: {financial_assets/total_assets*100:.2f}%")
print(f"经营资产占比: {operating_assets/total_assets*100:.2f}%")
```

### 2. 资本结构分析

```python
# 计算资本结构
total_capital = df_restructured[df_restructured['项目'] == '资本总额'][date].values[0]
total_debt = df_restructured[df_restructured['项目'] == '有息债务合计'][date].values[0]
total_equity = df_restructured[df_restructured['项目'] == '所有者权益合计'][date].values[0]

print(f"有息债务占比: {total_debt/total_capital*100:.2f}%")
print(f"所有者权益占比: {total_equity/total_capital*100:.2f}%")
```

### 3. 营运资金分析

```python
# 计算营运资金占用
working_capital = df_restructured[df_restructured['项目'] == '周转性经营投入合计'][date].values[0]

if working_capital > 0:
    print(f"企业需要占用营运资金: {working_capital:,.2f}")
else:
    print(f"企业营运资金为负，被占用: {-working_capital:,.2f}")
```

## 注意事项

1. **数据格式要求**
   - 输入数据必须是转置格式（字段名为行，日期为列）
   - 字段名可以是中文或英文，模块会自动识别

2. **缺失值处理**
   - 缺失值会被自动填充为0进行计算
   - 建议在使用前检查数据完整性

3. **数据验证**
   - 重构后建议验证：资产总额 = 金融资产 + 长期股权投资 + 经营资产
   - 注意：资本总额 ≠ 资产总额（因为资本总额只包含有息债务和所有者权益）

4. **金融企业特殊科目**
   - 模块已包含金融企业的特殊科目（如存款、准备金等）
   - 非金融企业这些科目通常为空，不影响计算

## 示例输出

```
资产结构:
  金融资产合计: 8,170,548,395.77
    - 货币资金: 4,497,065,241.00
    - 交易性金融资产: 3,615,062,634.00
  
  长期股权投资: 12,211,172.00
  
  经营资产合计: 3,891,347,893.18
    - 周转性经营投入合计: 2,056,040,998.83
    - 长期经营资产合计: 1,835,306,894.35

资本结构:
  有息债务合计: 1,389,520,635.03
    - 短期债务: 1,389,520,635.03
    - 长期债务: 0.00
  
  所有者权益合计: 15,528,408,225.05
    - 归属于母公司股东权益: 15,528,408,225.05
    - 少数股东权益: 0.00
```

## 参考资料

- 《财务报表分析与股票估值》（郭永清著）
- 《手把手教你读财报》（唐朝著）
- Tushare财务数据接口文档
