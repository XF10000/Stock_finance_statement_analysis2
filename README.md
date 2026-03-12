# 股票财务数据获取工具

基于 Tushare API 的股票财务数据获取工具，支持获取完整的财务报表数据（包括默认隐藏字段），并可将字段名翻译为中文。

## 功能特性

- ✅ 获取完整的财务数据（包括默认显示为 N 的隐藏字段）
- ✅ 支持四大财务报表：财务指标表、资产负债表、利润表、现金流量表
- ✅ **字段名自动翻译**：可将英文字段名翻译为中文，方便理解和使用
- ✅ 自动过滤上市前的无效数据
- ✅ 支持分页获取大数据量数据
- ✅ 支持错误重试机制
- ✅ 支持导出为 CSV 或 Excel 格式
- ✅ 完善的日志记录和错误处理

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 复制配置文件模板：

```bash
cp config.yaml.example config.yaml
```

2. 编辑 `config.yaml`，填入你的 Tushare Token：

```yaml
tushare:
  token: "你的Tushare Token"
```

## 股票代码格式说明

系统支持两种股票代码格式：

### 1. 简化格式（推荐）

只需输入6位股票代码数字，系统自动判断交易所：

```bash
python main.py 000333    # 自动识别为 000333.SZ（深圳）
python main.py 600519    # 自动识别为 600519.SH（上海）
python main.py 603345    # 自动识别为 603345.SH（上海）
```

**自动判断规则：**
- `000`、`002`、`003`、`300` 开头 → `.SZ`（深圳交易所）
- `600`、`601`、`603`、`605`、`688` 开头 → `.SH`（上海交易所）

### 2. 完整格式

也可以输入完整的股票代码（带交易所后缀）：

```bash
python main.py 000333.SZ
python main.py 600519.SH
```

## 使用方法

### 1. 命令行方式

获取单家公司的全部历史财务数据（默认：中文列名 + 转置格式）：

```bash
# 简化格式：只需股票代码数字
python main.py 000333

# 也支持完整格式
python main.py 600519.SH
```

获取指定日期范围的数据：

```bash
python main.py 600519.SH --start-date 20200101 --end-date 20231231
```

保存为 Excel 格式：

```bash
python main.py 000858.SZ --format excel
```

同时保存 CSV 和 Excel：

```bash
python main.py 000333.SZ --format both
```

**使用原始格式**（字段横向，时间纵向）：

```bash
python main.py 600519.SH --no-transpose
```

**使用英文列名**（不翻译）：

```bash
python main.py 600519.SH --no-translate
```

**组合使用**：

```bash
# 原始格式 + Excel 输出
python main.py 000001.SZ --no-transpose --format excel

# 英文列名 + 原始格式
python main.py 000001.SZ --no-translate --no-transpose
```

### 2. Python 代码方式

```python
from tushare_client import TushareClient

# 初始化客户端
client = TushareClient(config_path='config.yaml')

# 获取全部财务数据（英文字段）
data = client.get_all_financial_data('000001.SZ')

# 获取全部财务数据（中文字段，推荐）
data_cn = client.get_all_financial_data('000001.SZ', translate=True)

# 保存数据
client.save_to_csv(data_cn, '000001.SZ')

# 查看数据（中文列名更易读）
print(data_cn['fina_indicator'].head())
```

### 3. 数据格式说明

#### 字段翻译功能

**默认行为：所有字段名自动翻译为中文**

所有财务报表字段都支持中英文对照，包括：
- **财务指标表**：180 个字段
- **资产负债表**：156 个字段  
- **利润表**：94 个字段
- **现金流量表**：99 个字段

**翻译对比示例：**

| 英文字段名 | 中文含义 |
|-----------|---------|
| `eps` | 基本每股收益 |
| `roe` | 净资产收益率 |
| `accounts_receiv` | 应收账款 |
| `total_assets` | 资产总计 |
| `net_profit` | 净利润 |

默认输出的 CSV/Excel 文件使用中文列名，更便于理解和分析。

如果需要英文列名，使用 `--no-translate` 参数或设置 `translate=False`。

#### 数据转置功能

**默认行为：自动转置为分析友好格式**

系统默认使用转置格式，更适合财务数据分析：

**转置格式**（默认）：
```
字段名, 20241231, 20240930, 20240630, ...
基本每股收益, 2.15, 1.94, 1.23, ...
净资产收益率, 10.08, 9.10, 5.79, ...
应收账款, 815944069, 830587000, 850000000, ...
资产总计, 20408219467, 19800000000, 19500000000, ...
```

**原始格式**（使用 `--no-transpose` 参数）：
```
TS代码, 公告日期, 报告期, 基本每股收益, 净资产收益率, ...
000001.SZ, 20250315, 20241231, 2.15, 10.08, ...
000001.SZ, 20241019, 20240930, 1.94, 9.10, ...
```

**转置格式的优势：**
- ✅ 更容易对比不同时期的财务数据
- ✅ 适合横向分析和趋势观察
- ✅ Excel 中更方便查看大量字段
- ✅ 符合财务分析习惯

### 4. 运行示例

```bash
python example_usage.py
```

### 5. 测试翻译功能

```bash
python test_translation.py
```

## 数据说明

### 获取的字段策略

本项目获取**所有字段**，无论 Tushare 文档中标记的"默认显示"是 Y 还是 N。

这是因为许多重要字段（如 `receiv_financing` 应收款项融资、`contract_assets` 合同资产等）默认不显示，但对财务分析非常重要。

### 四大财务报表

| 报表类型 | 字段数量 | 说明 |
|---------|---------|------|
| 财务指标表 (fina_indicator) | 约 180 个 | 综合财务指标，包括每股指标、盈利能力、营运能力、偿债能力等 |
| 资产负债表 (balancesheet) | 约 156 个 | 反映企业特定时点的财务状况 |
| 利润表 (income) | 约 94 个 | 反映企业一定时期内的经营成果 |
| 现金流量表 (cashflow) | 约 99 个 | 反映企业现金流入和流出情况 |

### 输出文件格式

运行后会在 `data` 目录生成以下文件：

```
data/
├── 000001.SZ_fina_indicator.csv   # 财务指标表
├── 000001.SZ_balancesheet.csv      # 资产负债表
├── 000001.SZ_income.csv            # 利润表
└── 000001.SZ_cashflow.csv          # 现金流量表
```

如果选择 Excel 格式，会生成一个包含多个 sheet 的 Excel 文件。

## API 方法说明

### TushareClient 类

#### 主要方法

| 方法 | 说明 |
|------|------|
| `get_fina_indicator(ts_code, start_date, end_date)` | 获取财务指标表 |
| `get_balancesheet(ts_code, start_date, end_date)` | 获取资产负债表 |
| `get_income(ts_code, start_date, end_date)` | 获取利润表 |
| `get_cashflow(ts_code, start_date, end_date)` | 获取现金流量表 |
| `get_all_financial_data(ts_code, start_date, end_date)` | 获取全部财务数据 |
| `save_to_csv(data, ts_code, output_dir)` | 保存为 CSV |
| `save_to_excel(data, ts_code, output_dir)` | 保存为 Excel |

#### 参数说明

- `ts_code`: 股票代码，格式为 `代码.交易所`（如 `000001.SZ`）
  - SZ: 深圳证券交易所
  - SH: 上海证券交易所
- `start_date`: 开始日期，格式 `YYYYMMDD`（可选）
- `end_date`: 结束日期，格式 `YYYYMMDD`（可选）

## 注意事项

1. **Tushare 积分要求**：不同接口对积分有不同要求，积分不足可能导致部分数据无法获取
2. **请求频率限制**：代码已内置请求间隔控制，避免触发 API 限流
3. **数据量**：获取全部历史数据可能需要较长时间，建议在非高峰期运行
4. **数据过滤**：自动过滤上市前的无效数据，确保数据准确性

## 项目结构

```
Stock_finance_statement_analysis2/
├── config.yaml              # 配置文件（包含 Token）
├── requirements.txt         # Python 依赖
├── tushare_client.py        # Tushare 客户端核心类
├── main.py                  # 命令行入口
├── example_usage.py         # 使用示例
├── docs/
│   └── Tushare_Fields_Documentation.md  # 字段文档
├── data/                    # 数据输出目录
└── logs/                    # 日志目录
```

## 常见问题

### 1. Token 错误

确保 `config.yaml` 中的 token 正确无误，且已复制到项目根目录。

### 2. 积分不足

部分高级接口需要足够的 Tushare 积分，可通过以下方式获取积分：
- 注册并完善个人信息
- 每日签到
- 分享项目
- 捐赠支持

### 3. 数据为空

可能原因：
- 股票代码错误
- 日期范围内无数据
- 积分不足无法访问该接口

### 4. 请求超时

网络问题或 API 响应慢，代码会自动重试 3 次。

## 参考文档

- [Tushare 官方文档](https://tushare.pro/document/2)
- [财务指标表接口](https://tushare.pro/document/2?doc_id=79)
- [资产负债表接口](https://tushare.pro/document/2?doc_id=36)
- [利润表接口](https://tushare.pro/document/2?doc_id=33)
- [现金流量表接口](https://tushare.pro/document/2?doc_id=44)

## License

MIT License
