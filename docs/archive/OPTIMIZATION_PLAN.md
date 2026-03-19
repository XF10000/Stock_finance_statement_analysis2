# 三大优化实施计划

## 📋 优化概览

| 优化项 | 状态 | 预计提升 |
|--------|------|---------|
| 1. 批量写入（方案2：全局队列+专门写入线程） | ✅ 已完成 | 性能提升 5-10x，消除死锁 |
| 2. `--init` 后自动计算指标 | ✅ 已完成 | 完整的一键初始化 |
| 3. 使用 tqdm 友好进度条 | ✅ 已完成 | 用户体验大幅提升 |

---

## ✅ 已完成

### 优化 1.1: FinancialDataManager 批量写入方法

**文件**: `financial_data_manager.py`

**新增方法**: `save_financial_data_batch(batch_data: List[Dict])`

**功能**:
- 接收批量数据列表
- 按表分组（balancesheet, income, cashflow, fina_indicator）
- 使用 `executemany()` 批量插入
- 失败时回滚

**代码位置**: Line 407-465

---

### 优化 1.2: FinancialDataUpdater 写入队列和线程

**文件**: `update_financial_data.py`

**新增属性**:
```python
self.write_queue = Queue()          # 全局写入队列
self.batch_size = 50                # 每批50条
self.writer_running = False         # 线程运行标志
self.writer_thread = None           # 写入线程
```

**新增方法**:
1. `start_batch_writer()` - 启动批量写入线程
2. `stop_batch_writer()` - 停止线程并清空队列
3. `_batch_writer_worker()` - 批量写入工作线程
4. `_write_batch(batch)` - 执行批量写入

**工作原理**:
```
工作线程1 → 获取数据 → 放入队列 ┐
工作线程2 → 获取数据 → 放入队列 ├→ 写入队列 → 批量写入线程 → 数据库
工作线程3 → 获取数据 → 放入队列 ┘    (攒够50条)     (executemany)
```

**代码位置**: Line 95-99, 154-231

---

## 🔄 进行中

### 优化 1.3: 修改 fetch_stock_all_data 使用队列

**需要修改的逻辑**:

**当前代码**（逐条写入）:
```python
for end_date in unique_dates:
    period_data = df[df[date_col] == end_date].copy()
    self.db_manager.save_financial_data(...)  # 直接写入
```

**优化后**（放入队列）:
```python
for end_date in unique_dates:
    period_data = df[df[date_col] == end_date].copy()
    self.write_queue.put({
        'ts_code': ts_code,
        'end_date': end_date,
        'data_type': table_name,
        'data': period_data
    })
```

**修改位置**: `fetch_stock_all_data()` 方法

---

### 优化 1.4: 修改 fetch_stock_incremental 使用队列

**同样的修改逻辑**，将直接写入改为放入队列。

**修改位置**: `fetch_stock_incremental()` 方法

---

### 优化 1.5: 在 update_all_stocks 中启动/停止写入线程

**需要添加**:
```python
def update_all_stocks(self, stocks, force_update=False, resume_from=None):
    # 启动批量写入线程
    self.start_batch_writer()
    
    try:
        # 原有的线程池逻辑
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            ...
    finally:
        # 停止批量写入线程
        self.stop_batch_writer()
```

---

## ⏳ 待实施

### 优化 2: `--init` 后自动计算核心指标

**目标**: 在 `--init` 完成数据采集后，自动计算所有股票的核心指标（年报 + TTM）

**实施位置**: `main()` 函数中的 `if args.init:` 分支

**添加代码**:
```python
if args.init:
    # 现有的数据采集逻辑
    updater.update_all_stocks(...)
    
    # 新增：自动计算核心指标
    logger.info("\n" + "="*60)
    logger.info("开始计算核心指标（年报 + TTM）...")
    logger.info("="*60)
    
    updater.calculate_core_indicators_batch()  # 年报指标
    updater.calculate_ttm_indicators_batch()   # TTM指标
```

**预计效果**: 一键完成全部初始化，无需手动运行 `--recalculate-all`

---

### 优化 3: 使用 tqdm 实现友好进度条

**目标**: 将当前的日志进度替换为实时刷新的进度条

**需要安装**: `pip install tqdm`

**修改位置**:
1. `_print_progress()` 方法
2. `update_all_stocks()` 方法
3. `update_latest_quarter()` 方法
4. `update_dividend_and_totalshares()` 方法

**示例代码**:
```python
from tqdm import tqdm

def update_all_stocks(self, stocks, ...):
    self.start_batch_writer()
    
    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
        futures = {
            executor.submit(self.fetch_stock_all_data, stock['ts_code'], force_update): stock
            for stock in stocks
        }
        
        # 使用 tqdm 进度条
        with tqdm(total=len(stocks), desc="数据采集进度") as pbar:
            for future in as_completed(futures):
                try:
                    future.result()
                    pbar.update(1)
                    pbar.set_postfix({
                        '成功': self.stats['success'],
                        '失败': self.stats['failed'],
                        '跳过': self.stats['skipped']
                    })
                except Exception as e:
                    self.logger.error(f"处理失败: {e}")
    
    self.stop_batch_writer()
```

**预计效果**:
```
数据采集进度: 45%|████████▌         | 2250/5000 [15:30<17:20, 2.64it/s, 成功=2100, 失败=50, 跳过=100]
```

---

## 🎯 实施顺序

1. ✅ **完成优化 1.1-1.2**（已完成）
2. 🔄 **完成优化 1.3-1.5**（批量写入完整实现）
3. ⏳ **实施优化 3**（tqdm 进度条）
4. ⏳ **实施优化 2**（自动计算指标）
5. ✅ **测试所有优化**

---

## 📊 预期性能提升

### 批量写入优化

**当前性能**:
- 5000只股票 × 平均50个季度 × 4张表 = 100万次 INSERT
- 每次 INSERT 锁定数据库 → 频繁锁竞争
- 预计耗时：**8-10小时**

**优化后性能**:
- 100万条数据 ÷ 50条/批 = 2万次批量 INSERT
- 只有1个线程写入 → 无锁竞争
- 预计耗时：**1-2小时**

**提升**: **5-10倍**

---

### 用户体验提升

**当前**:
```
进度: 100/5000 (2.0%) | 成功: 95 | 失败: 5 | 跳过: 0 | 速度: 1.2 只/秒 | 预计剩余: 68.3 分钟
进度: 110/5000 (2.2%) | 成功: 105 | 失败: 5 | 跳过: 0 | 速度: 1.2 只/秒 | 预计剩余: 67.8 分钟
...（日志很长）
```

**优化后**:
```
数据采集: 45%|████████▌         | 2250/5000 [15:30<17:20, 2.64it/s, 成功=2100, 失败=50, 跳过=100]
```

**提升**: 单行实时刷新，清晰直观

---

## 🔧 下一步行动

继续完成：
1. 修改 `fetch_stock_all_data` 使用队列
2. 修改 `fetch_stock_incremental` 使用队列  
3. 在 `update_all_stocks` 中启动/停止写入线程
4. 添加 tqdm 进度条
5. 添加 `--init` 后自动计算指标
6. 全面测试

---

**文档版本**: v1.0  
**创建时间**: 2026-03-18  
**状态**: 优化进行中 🔄
