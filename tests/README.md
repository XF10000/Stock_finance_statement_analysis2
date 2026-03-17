# 测试套件说明

## 安装测试依赖

```bash
pip install pytest pytest-cov
```

## 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定测试文件
```bash
pytest tests/test_market_data_manager.py
```

### 运行特定测试类
```bash
pytest tests/test_market_data_manager.py::TestMarketDataManager
```

### 运行特定测试函数
```bash
pytest tests/test_market_data_manager.py::TestMarketDataManager::test_init_database
```

### 显示详细输出
```bash
pytest -v
```

### 显示打印输出
```bash
pytest -s
```

### 生成覆盖率报告
```bash
pytest --cov=. --cov-report=html
```

### 只运行失败的测试
```bash
pytest --lf
```

### 并行运行测试（需要 pytest-xdist）
```bash
pip install pytest-xdist
pytest -n auto
```

## 测试文件说明

- `conftest.py`: pytest 配置和共享 fixtures
- `test_market_data_manager.py`: 测试数据库管理器
- `test_core_indicators_analyzer.py`: 测试核心指标计算
- `test_market_analyzer.py`: 测试市场分析器
- `test_integration.py`: 集成测试

## 测试覆盖范围

### 单元测试
- ✅ 数据库初始化
- ✅ 数据保存和读取
- ✅ 核心指标计算
- ✅ 分位数计算
- ✅ 多线程安全性

### 集成测试
- ✅ 完整数据流程
- ✅ 增量更新逻辑
- ✅ 数据一致性

### 边界测试
- ✅ 空数据处理
- ✅ 缺失字段处理
- ✅ 异常值处理
- ✅ 除零错误处理

## 持续集成

可以在 CI/CD 流程中添加：

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest --cov=. --cov-report=xml
```
