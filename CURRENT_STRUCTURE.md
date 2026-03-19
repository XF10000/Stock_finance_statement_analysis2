# 当前项目结构

**更新时间**: 2026年3月19日  
**状态**: 已完成第一阶段整理

---

## 📁 当前目录结构

```
Stock_finance_statement_analysis2/
│
├── README.md                          # 项目主文档
├── requirements.txt                   # Python依赖
├── config.yaml.example                # 配置模板
├── config.yaml -> config/config.yaml  # 配置文件（软链接）
├── pytest.ini                         # pytest配置
├── .gitignore                         # Git忽略文件
│
├── docs/                              # 📚 文档目录（已整理）
│   ├── README.md                      # 文档索引
│   ├── quick_start.md                 # 快速开始
│   ├── features.md                    # 功能清单
│   ├── database.md                    # 数据库说明
│   ├── architecture.md                # 代码架构
│   ├── project_summary.md             # 项目总结
│   ├── optimization_history.md        # 优化历史
│   ├── archive/                       # 历史文档归档
│   ├── 参考/                          # 参考资料
│   └── 图表汇总/                      # 图表文件
│
├── config/                            # ⚙️ 配置目录（已整理）
│   └── config.yaml                    # 主配置文件
│
├── logs/                              # 📝 日志目录（已整理）
│   ├── update_financial_data.log
│   └── update_market_data.log
│
├── data/                              # 📊 数据目录（已整理）
│   ├── output/                        # 输出文件
│   │   ├── csv/                       # CSV文件
│   │   ├── excel/                     # Excel文件
│   │   └── html/                      # HTML报告
│   ├── temp/                          # 临时文件
│   └── test/                          # 测试数据
│
├── database/                          # 💾 数据库目录
│   └── financial_data.db              # SQLite数据库
│
├── tests/                             # 🧪 测试目录
│   ├── __init__.py
│   ├── conftest.py
│   └── test_*.py                      # 测试文件
│
├── test_results/                      # 测试结果
│
├── Python源代码文件（17个）           # ⚠️ 待整理到src/目录
│   ├── tushare_client.py
│   ├── financial_data_manager.py
│   ├── balance_sheet_restructure.py
│   ├── income_statement_restructure.py
│   ├── cashflow_statement_restructure.py
│   ├── field_mapping.py
│   ├── core_indicators_analyzer.py
│   ├── annual_report_generator.py
│   ├── ttm_generator.py
│   ├── financial_data_analyzer.py
│   ├── html_report_generator.py
│   ├── summary_excel_generator.py
│   ├── fcff_report_generator.py
│   ├── final_report_generator_echarts.py
│   ├── update_financial_data.py
│   ├── main.py
│   └── fetch_all_a_shares_safe.py
│
└── PROJECT_STRUCTURE.md               # 标准结构方案文档
```

---

## ✅ 已完成的整理

### 1. 文档目录（docs/）
- ✅ 所有文档文件已移动到 `docs/` 目录
- ✅ 文档已重命名为英文（便于跨平台）
- ✅ 历史文档已归档到 `docs/archive/`
- ✅ 创建了文档索引 `docs/README.md`

**文档列表**:
- `docs/README.md` - 文档索引
- `docs/quick_start.md` - 快速开始
- `docs/features.md` - 功能清单
- `docs/database.md` - 数据库说明
- `docs/architecture.md` - 代码架构
- `docs/project_summary.md` - 项目总结
- `docs/optimization_history.md` - 优化历史

### 2. 配置目录（config/）
- ✅ 配置文件移动到 `config/` 目录
- ✅ 创建软链接保持向后兼容
- ✅ 配置模板保留在根目录

### 3. 日志目录（logs/）
- ✅ 所有日志文件移动到 `logs/` 目录
- ✅ 日志文件集中管理

### 4. 数据目录（data/）
- ✅ 创建了规范的输出目录结构
  - `data/output/csv/` - CSV文件
  - `data/output/excel/` - Excel文件
  - `data/output/html/` - HTML报告
- ✅ 创建了临时文件目录 `data/temp/`

---

## ⚠️ 待整理项

### Python代码文件（17个）
**当前状态**: 所有.py文件仍在根目录  
**建议**: 按照 `PROJECT_STRUCTURE.md` 中的方案整理到 `src/` 目录

**原因暂未整理**:
1. 需要修改大量导入路径
2. 需要创建 `__init__.py` 文件
3. 需要充分测试确保功能正常
4. 风险较高，建议分步进行

**下一步建议**:
1. 创建 `src/` 目录结构
2. 复制文件到新位置（保留原文件）
3. 创建 `__init__.py` 文件
4. 更新导入路径
5. 测试新结构
6. 确认无误后删除旧文件

---

## 📊 整理进度

| 项目 | 状态 | 进度 |
|------|------|------|
| 文档整理 | ✅ 完成 | 100% |
| 配置整理 | ✅ 完成 | 100% |
| 日志整理 | ✅ 完成 | 100% |
| 数据目录 | ✅ 完成 | 100% |
| 代码整理 | ⏳ 待进行 | 0% |

**总体进度**: 约 60% 完成

---

## 🎯 优势

### 已实现的优势
1. ✅ 文档集中管理，易于查找
2. ✅ 日志文件不再污染根目录
3. ✅ 配置文件集中管理
4. ✅ 数据输出有明确的分类
5. ✅ 保持向后兼容（通过软链接）

### 待实现的优势
1. ⏳ 代码模块化组织
2. ⏳ 清晰的包结构
3. ⏳ 更好的可维护性
4. ⏳ 支持 pip 安装

---

## 🔧 使用说明

### 当前使用方式（不变）
所有命令保持不变，因为：
1. Python文件仍在根目录
2. 配置文件通过软链接访问
3. 数据库路径未改变

```bash
# 数据更新（不变）
python update_financial_data.py --update-latest

# 报告生成（不变）
python main.py 000333

# 配置文件（自动使用软链接）
# config.yaml -> config/config.yaml
```

### 文档访问（新位置）
```bash
# 查看文档索引
cat docs/README.md

# 查看快速开始
cat docs/quick_start.md

# 查看功能清单
cat docs/features.md
```

### 日志查看（新位置）
```bash
# 查看更新日志
tail -f logs/update_financial_data.log

# 查看所有日志
ls logs/
```

---

## 📝 注意事项

1. **配置文件**: 现在实际位置在 `config/config.yaml`，但通过软链接仍可使用 `config.yaml`
2. **日志文件**: 新的日志会自动写入 `logs/` 目录（需要更新代码中的日志路径）
3. **数据输出**: 建议将输出路径改为 `data/output/` 下的对应目录
4. **向后兼容**: 当前所有功能保持不变

---

## 🚀 下一步计划

### 短期（可选）
1. 更新代码中的日志路径指向 `logs/` 目录
2. 更新数据输出路径指向 `data/output/` 目录
3. 测试所有功能确保正常

### 中期（建议）
1. 按照 `PROJECT_STRUCTURE.md` 创建 `src/` 目录
2. 逐步迁移代码文件
3. 更新导入路径
4. 充分测试

### 长期（可选）
1. 添加 `setup.py` 支持
2. 发布为Python包
3. 完善CI/CD

---

## 📚 相关文档

- `PROJECT_STRUCTURE.md` - 标准项目结构方案（详细规划）
- `docs/README.md` - 文档索引
- `README.md` - 项目主文档

---

**文档版本**: 1.0  
**创建时间**: 2026年3月19日
