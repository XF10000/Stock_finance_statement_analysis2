# 总股本和分红数据持久化开发计划

## 项目目标

将总股本和分红数据持久化到本地数据库，实现模块化分工：
- **update_financial_data.py**: 负责所有数据采集与存储（包括财务数据、总股本、分红）
- **main.py**: 负责数据分析与报告生成（完全从数据库读取，不再调用 Tushare API）

## 开发阶段

### Phase 1: 数据库表结构设计
**目标**: 在 FinancialDataManager 中添加总股本表和分红表的创建逻辑

**任务清单**:
- [ ] 1.1 设计 `total_share` 表结构
  - 字段: ts_code, end_date, total_share, update_time
  - 主键: (ts_code, end_date)
  - 索引: ts_code, end_date

- [ ] 1.2 设计 `dividend` 表结构
  - 字段: ts_code, end_date, ann_date, div_proc, stk_div, stk_bo_rate, stk_co_rate, cash_div, cash_div_tax, record_date, ex_date, pay_date, div_listdate, imp_ann_date, update_time
  - 主键: (ts_code, end_date, ann_date)
  - 索引: ts_code, end_date

- [ ] 1.3 在 FinancialDataManager.__init__() 中添加表创建 SQL
- [ ] 1.4 测试数据库表创建功能

**预计耗时**: 1-2 小时

---

### Phase 2: 扩展 FinancialDataManager
**目标**: 添加总股本和分红数据的存储和读取方法

**任务清单**:
- [ ] 2.1 实现 `save_total_share_data(ts_code, end_date, total_share)` 方法
  - 支持单条和批量插入
  - 使用 INSERT OR REPLACE 避免重复

- [ ] 2.2 实现 `get_total_share_data(ts_code, start_date=None, end_date=None)` 方法
  - 返回 DataFrame 格式
  - 支持日期范围筛选

- [ ] 2.3 实现 `save_dividend_data(ts_code, dividend_df)` 方法
  - 支持 DataFrame 批量插入
  - 处理字段映射（中英文）

- [ ] 2.4 实现 `get_dividend_data(ts_code, start_date=None, end_date=None)` 方法
  - 返回 DataFrame 格式
  - 支持日期范围筛选

- [ ] 2.5 实现 `check_total_share_exists(ts_code, end_date)` 检查方法
- [ ] 2.6 实现 `check_dividend_exists(ts_code, end_date)` 检查方法
- [ ] 2.7 编写单元测试验证所有方法

**预计耗时**: 3-4 小时

---

### Phase 3: 修改 update_financial_data.py
**目标**: 在数据采集流程中增加总股本和分红数据的获取与存储

**任务清单**:
- [ ] 3.1 将 main.py 中的 `get_total_share_data()` 函数迁移到 FinancialDataUpdater 类
  - 重命名为 `fetch_total_share_data(ts_code, balance_df)`
  - 适配限流器

- [ ] 3.2 将 main.py 中的 `get_dividend_data()` 函数迁移到 FinancialDataUpdater 类
  - 重命名为 `fetch_dividend_data(ts_code)`
  - 适配限流器
  - 移除 Excel 保存逻辑（只存数据库）

- [ ] 3.3 在 `fetch_stock_all_data()` 中增加总股本和分红数据采集
  - 在获取四张财务报表后
  - 调用 `fetch_total_share_data()` 和 `fetch_dividend_data()`
  - 使用 db_manager 保存到数据库

- [ ] 3.4 在 `fetch_stock_incremental()` 中增加增量更新逻辑
  - 检查目标季度是否已有总股本数据
  - 检查是否已有分红数据
  - 按需更新

- [ ] 3.5 添加统计信息
  - 在进度报告中显示总股本和分红数据的获取情况

- [ ] 3.6 测试批量更新流程

**预计耗时**: 4-5 小时

---

### Phase 4: 重构 main.py
**目标**: 移除 Tushare API 依赖，改为从数据库读取所有数据

**任务清单**:
- [ ] 4.1 移除 `get_total_share_data()` 函数定义
- [ ] 4.2 移除 `get_dividend_data()` 函数定义
- [ ] 4.3 移除 `add_total_share_to_balance()` 函数（或改为从数据库读取）

- [ ] 4.4 修改 main() 函数主流程
  - 移除 TushareClient 初始化
  - 移除 client.get_all_financial_data() 调用
  - 改为从 FinancialDataManager 读取财务数据

- [ ] 4.5 实现数据完整性检查
  - 检查数据库是否有该股票的数据
  - 如果缺失，给出明确提示和解决方案
  - 显示数据最后更新时间

- [ ] 4.6 修改总股本数据获取逻辑
  - 从 db_manager.get_total_share_data() 读取
  - 添加到资产负债表重构流程

- [ ] 4.7 修改分红数据获取逻辑
  - 从 db_manager.get_dividend_data() 读取
  - 可选保存为 Excel（保留用户友好功能）

- [ ] 4.8 更新命令行参数
  - 移除不再需要的参数（如 --start-date, --end-date）
  - 或将其用于筛选数据库中的数据范围

- [ ] 4.9 更新帮助文档和提示信息

**预计耗时**: 3-4 小时

---

### Phase 5: 测试验证
**目标**: 测试数据采集、存储、读取的完整流程

**任务清单**:
- [ ] 5.1 测试场景 1: 全新股票数据采集
  - 运行 `python update_financial_data.py --init` 采集少量股票
  - 验证四张财务表 + 总股本 + 分红数据都已入库
  - 检查数据完整性

- [ ] 5.2 测试场景 2: 增量更新
  - 运行 `python update_financial_data.py --update-latest`
  - 验证最新季度的所有数据都已更新

- [ ] 5.3 测试场景 3: main.py 单股分析（数据库模式）
  - 运行 `python main.py 000333`
  - 验证能正确从数据库读取所有数据
  - 验证报表重构、报告生成功能正常

- [ ] 5.4 测试场景 4: 数据缺失处理
  - 对未入库的股票运行 main.py
  - 验证错误提示友好且有指导意义

- [ ] 5.5 测试场景 5: 边界情况
  - 测试没有分红记录的股票
  - 测试总股本数据缺失的情况
  - 验证程序健壮性

- [ ] 5.6 性能测试
  - 测试批量更新 100 只股票的耗时
  - 验证 API 限流是否生效
  - 检查数据库查询性能

**预计耗时**: 3-4 小时

---

### Phase 6: 文档更新
**目标**: 更新 README 和使用说明文档

**任务清单**:
- [ ] 6.1 更新 README.md
  - 更新项目架构说明
  - 更新模块职责划分
  - 更新数据库表结构文档

- [ ] 6.2 更新快速开始文档
  - 更新首次使用流程（先运行 update_financial_data.py）
  - 更新 main.py 使用说明

- [ ] 6.3 创建数据库迁移指南
  - 为现有用户提供数据迁移方案
  - 说明如何补充总股本和分红数据

- [ ] 6.4 更新 config.yaml.example
  - 添加数据库配置说明

- [ ] 6.5 编写常见问题 FAQ
  - 数据缺失怎么办？
  - 如何更新数据？
  - 如何查看数据库状态？

**预计耗时**: 2-3 小时

---

## 总体时间估算

- **Phase 1**: 1-2 小时
- **Phase 2**: 3-4 小时
- **Phase 3**: 4-5 小时
- **Phase 4**: 3-4 小时
- **Phase 5**: 3-4 小时
- **Phase 6**: 2-3 小时

**总计**: 16-22 小时（约 2-3 个工作日）

---

## 风险与注意事项

### 技术风险
1. **数据迁移风险**: 现有用户可能已有部分数据，需要提供平滑迁移方案
2. **API 限流**: 批量获取总股本和分红数据可能触发限流，需要合理控制请求频率
3. **数据一致性**: 确保总股本数据的报告期与财务报表对齐

### 兼容性考虑
1. **向后兼容**: 考虑是否保留 main.py 的 API 模式作为备选方案
2. **数据库版本**: 为数据库添加版本号，便于未来升级

### 优化建议
1. **批量插入优化**: 总股本和分红数据可以批量插入以提高性能
2. **缓存机制**: 考虑为常用查询添加缓存
3. **增量更新**: 只更新缺失或过期的数据，避免重复请求

---

## 成功标准

1. ✅ 数据库中成功存储总股本和分红数据
2. ✅ update_financial_data.py 能够完整采集所有类型的数据
3. ✅ main.py 完全不依赖 Tushare API，只从数据库读取
4. ✅ 所有测试场景通过
5. ✅ 文档完整更新
6. ✅ 代码通过 code review

---

## 后续优化方向

1. **数据质量监控**: 添加数据完整性检查和异常监控
2. **自动化任务**: 设置定时任务自动更新最新季度数据
3. **数据可视化**: 为总股本和分红数据添加可视化图表
4. **API 封装**: 为数据库访问提供统一的 API 接口
5. **多数据源支持**: 未来可以支持其他数据源（如东方财富、同花顺等）

---

## 进度跟踪

| 阶段 | 状态 | 开始时间 | 完成时间 | 负责人 | 备注 |
|------|------|----------|----------|--------|------|
| Phase 1 | 待开始 | - | - | - | - |
| Phase 2 | 待开始 | - | - | - | - |
| Phase 3 | 待开始 | - | - | - | - |
| Phase 4 | 待开始 | - | - | - | - |
| Phase 5 | 待开始 | - | - | - | - |
| Phase 6 | 待开始 | - | - | - | - |

---

**文档版本**: v1.0  
**创建时间**: 2026-03-18  
**最后更新**: 2026-03-18
