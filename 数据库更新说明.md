# 数据库更新使用说明

## 概述

本项目使用SQLite数据库（`database/financial_data.db`）存储全A股财务数据和核心指标。数据库包含：

- **股票列表**：全A股基本信息
- **四大财务报表**：资产负债表、利润表、现金流量表、财务指标
- **核心指标**：四大核心财务指标及分位数
- **市场分布**：全A股指标分布统计

---

## 一、增量更新（推荐）

### 适用场景
- **年报季**（1-4月）：更新上一年Q4数据
- **一季报季**（5-8月）：更新当年Q1数据
- **半年报季**（9-10月）：更新当年Q2数据
- **三季报季**（11-12月）：更新当年Q3数据

### 使用方法

#### 方法1：自动判断最新季度（推荐）

```bash
# 自动判断当前应该更新哪个季度，并自动计算核心指标
python update_financial_data.py --update-latest
```

**执行流程**：
1. 自动判断目标季度（如现在是2025年3月，会更新2024Q4数据）
2. 检查数据库中哪些股票缺少该季度数据
3. 从Tushare获取缺失的数据
4. 保存到数据库
5. **自动计算核心指标**
6. 显示更新统计

**输出示例**：
```
============================================================
增量更新最新季度数据
============================================================
目标季度: 20241231
股票总数: 5234

进度: 100/5234 (1.9%) | 成功: 85 | 失败: 3 | 跳过: 12 | ...
进度: 5234/5234 (100.0%) | 成功: 4856 | 失败: 45 | 跳过: 333

============================================================
数据更新完成
============================================================
总计: 5234 只股票
成功: 4856 只
失败: 45 只
跳过: 333 只（已有数据）
总耗时: 45.2 分钟

============================================================
开始计算核心指标...
============================================================
进度: 100/5234 | 成功: 98 | 失败: 2
...
核心指标计算完成: 成功 4823 只，失败 411 只
```

#### 方法2：指定季度更新

```bash
# 更新2024年年报数据
python update_financial_data.py --update-latest --quarter 20241231

# 更新2025年一季报数据
python update_financial_data.py --update-latest --quarter 20250331
```

#### 方法3：只更新数据，不计算指标

```bash
# 如果只想更新原始数据，稍后再计算指标
python update_financial_data.py --update-latest --no-indicators
```

#### 方法4：指定季度 + 关闭指标 + 自定义数据库路径

```bash
# 例：在备用数据库中更新2024Q4，但暂时不算指标
python update_financial_data.py \
    --update-latest \
    --quarter 20241231 \
    --no-indicators \
    --db database/market_data_test.db
```

### 优点
- ⚡ **速度快**：只获取新季度数据，通常30-60分钟完成
- 💰 **省积分**：API调用次数少
- 🔄 **智能跳过**：已有数据自动跳过
- 📊 **自动计算**：更新后自动计算核心指标

---

## 二、全量更新

### 适用场景
- 首次建立数据库
- 数据库损坏需要重建
- 新增股票到数据库
- 定期完整更新（建议每年一次）

### 使用方法

#### 首次初始化（获取全部历史数据）

```bash
# 首次运行，获取全A股所有历史数据
python update_financial_data.py --init
```

**注意**：
- ⏰ 耗时较长：约6-12小时（取决于网络和API限流）
- 💰 消耗积分：约200-500积分
- 📦 数据量大：生成的数据库约4GB

#### 强制重新获取

```bash
# 强制更新所有股票（忽略已有数据）
python update_financial_data.py --init --force
```

#### 断点续传

```bash
# 如果中途中断，从指定股票继续
python update_financial_data.py --init --resume 600519.SH
```

#### 重新计算全部核心指标

```bash
# 清空 core_indicators 表并重新计算所有历史数据
python update_financial_data.py --recalculate-all

# 只重算某个季度（如2024Q4）
python update_financial_data.py --recalculate-all --quarter 20241231
```

**说明**：
- 该命令使用“批量读取→内存计算→批量写回”的优化算法，12-20 分钟即可完成全市场重算
- 若不指定 `--quarter`，会按数据库中全部历史数据重新生成指标
- 可与 `--db`、`--config` 等参数搭配使用

---

## 三、核心指标说明

更新数据后，系统会自动计算以下核心指标并保存到 `core_indicators` 表：

### 四大核心指标

1. **报表逻辑一致性检验**
   - `ar_turnover_log`：应收账款周转率对数
   - `gross_margin`：毛利率

2. **再投资质量**
   - `lta_turnover_log`：长期经营资产周转率对数

3. **产业链地位**
   - `working_capital_ratio`：净营运资本比率

4. **真实盈利水平**
   - `ocf_ratio`：经营现金流比率

### 分位数数据

每个指标还包含在全A股中的分位数排名（`*_percentile`），用于横向对比。

---

## 四、常用命令速查

```bash
# 1. 增量更新（最常用）
python update_financial_data.py --update-latest

# 2. 指定季度增量更新
python update_financial_data.py --update-latest --quarter 20241231

# 3. 首次初始化
python update_financial_data.py --init

# 4. 查看帮助
python update_financial_data.py --help

# 5. 使用更多线程加速（默认5个）
python update_financial_data.py --update-latest --workers 10

# 6. 指定配置文件和数据库路径
python update_financial_data.py --update-latest \
    --config my_config.yaml \
    --db my_database.db

# 7. 强制重算全部核心指标
python update_financial_data.py --recalculate-all

# 8. 只重算某个季度的指标
python update_financial_data.py --recalculate-all --quarter 20241231
```

---

## 五、更新策略建议

### 日常维护

```
每季度财报发布后：
  - 4月底：更新上一年Q4数据
    python update_financial_data.py --update-latest --quarter 20241231
  
  - 8月底：更新当年Q1数据
    python update_financial_data.py --update-latest --quarter 20250331
  
  - 10月底：更新当年Q2数据
    python update_financial_data.py --update-latest --quarter 20250630
  
  - 次年1月：更新当年Q3数据
    python update_financial_data.py --update-latest --quarter 20250930
```

### 定期维护

```
每年一次：
  - 全量更新核心关注股票
  - 验证数据完整性
  - 数据库备份
```

---

## 六、数据库查询示例

### 使用Python查询

```python
from financial_data_manager import FinancialDataManager

# 初始化数据库管理器
db = FinancialDataManager('database/financial_data.db')

# 查询某只股票的核心指标
indicators = db.get_core_indicators('000333.SZ')
print(indicators)

# 查询某只股票的财务数据
balance = db.get_financial_data('000333.SZ', 'balancesheet')
income = db.get_financial_data('000333.SZ', 'income')

# 获取数据库统计
stats = db.get_database_stats()
print(stats)
```

### 使用SQL查询

```bash
# 使用sqlite3命令行工具
sqlite3 database/financial_data.db

# 查询示例
SELECT * FROM core_indicators 
WHERE ts_code = '000333.SZ' 
ORDER BY end_date DESC 
LIMIT 5;

# 查询ROIC排名前10的股票（2024Q4）
SELECT ts_code, ar_turnover_log, gross_margin, 
       lta_turnover_log, working_capital_ratio, ocf_ratio
FROM core_indicators
WHERE end_date = '20241231'
  AND ar_turnover_log IS NOT NULL
ORDER BY ar_turnover_log DESC
LIMIT 10;
```

---

## 七、常见问题

### Q1: 增量更新时提示"数据库中没有股票列表"？

**A**: 需要先运行 `--init` 初始化数据库：
```bash
python update_financial_data.py --init
```

### Q2: 更新速度慢怎么办？

**A**: 可以增加工作线程数（需要足够的API积分）：
```bash
python update_financial_data.py --update-latest --workers 10
```

### Q3: 如何查看更新日志？

**A**: 日志保存在 `update_financial_data.log` 文件中：
```bash
tail -f update_financial_data.log
```

### Q4: 核心指标计算失败怎么办？

**A**: 核心指标需要三大报表数据完整才能计算。部分股票可能因数据缺失而计算失败，这是正常现象。

### Q5: 数据库太大怎么办？

**A**: 可以定期清理旧数据或优化数据库：
```python
from financial_data_manager import FinancialDataManager
db = FinancialDataManager()
db.vacuum_database()  # 优化数据库，回收空间
```

---

## 八、数据库备份

### 备份命令

```bash
# 复制数据库文件
cp database/financial_data.db database/backup/market_data_$(date +%Y%m%d).db

# 或使用sqlite3导出
sqlite3 database/financial_data.db .dump > backup_$(date +%Y%m%d).sql
```

### 恢复数据库

```bash
# 从备份恢复
cp database/backup/market_data_20250316.db database/financial_data.db

# 或从SQL文件恢复
sqlite3 database/financial_data.db < backup_20250316.sql
```

---

## 九、性能优化建议

1. **使用SSD存储**：数据库文件较大，SSD可显著提升性能
2. **合理设置线程数**：根据API积分和网络状况调整
3. **定期优化数据库**：运行 `VACUUM` 命令回收空间
4. **分批更新**：如果股票数量太多，可以分批更新

---

## 十、技术支持

- **数据库结构**：参见 `docs/TECHNICAL_DOCUMENTATION.md`
- **核心指标说明**：参见 `docs/四大核心财务指标分析.md`
- **项目文档**：参见 `docs/USER_GUIDE.md`

---

**最后更新**: 2025-03-16
