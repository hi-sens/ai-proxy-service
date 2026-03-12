# 开发指南

## 代码质量工具配置

### 1. mypy - 类型检查

配置位于 `pyproject.toml`：

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
ignore_missing_imports = true
strict_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
check_untyped_defs = true
```

运行：
```bash
make type-check
# 或
mypy src/
```

### 2. isort - 导入排序

配置位于 `pyproject.toml`：

```toml
[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
skip_gitignore = true
```

运行：
```bash
isort src/ tests/
```

### 3. autoflake - 移除未使用的导入

自动移除：
- 未使用的导入
- 未使用的变量
- 重复的键

运行：
```bash
autoflake --in-place --remove-all-unused-imports --remove-unused-variables -r src/ tests/
```

### 4. black - 代码格式化

配置位于 `pyproject.toml`：

```toml
[tool.black]
line-length = 100
target-version = ['py311']
```

运行：
```bash
black src/ tests/
```

### 5. ruff - 快速 Linter

配置位于 `pyproject.toml`：

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]
```

运行：
```bash
ruff check src/ tests/
```

## Pre-commit Hooks

### 安装

```bash
make pre-commit
# 或
pre-commit install
```

### 配置

`.pre-commit-config.yaml` 包含以下 hooks：

1. **autoflake**: 移除未使用的导入和变量
2. **isort**: 排序导入
3. **black**: 格式化代码
4. **ruff**: 代码检查
5. **mypy**: 类型检查
6. **基础检查**:
   - 尾随空格
   - 文件结尾
   - YAML/JSON 验证
   - 大文件检查
   - 合并冲突检测
   - 私钥检测

### 手动运行

```bash
# 运行所有 hooks
pre-commit run --all-files

# 运行特定 hook
pre-commit run black --all-files
pre-commit run mypy --all-files
```

### 跳过 hooks（不推荐）

```bash
git commit --no-verify
```

## 开发工作流

### 1. 开始新功能

```bash
# 创建新分支
git checkout -b feature/your-feature

# 确保代码质量
make format
make check
```

### 2. 提交代码

```bash
# 添加文件
git add .

# 提交（会自动运行 pre-commit hooks）
git commit -m "feat: your feature description"

# 如果 hooks 失败，修复问题后重新提交
make format
git add .
git commit -m "feat: your feature description"
```

### 3. 推送代码

```bash
git push origin feature/your-feature
```

## Makefile 命令

```bash
make help           # 查看所有可用命令
make install        # 安装生产依赖
make dev-install    # 安装开发依赖
make format         # 格式化代码
make lint           # 代码检查
make type-check     # 类型检查
make test           # 运行测试
make test-cov       # 运行测试并生成覆盖率报告
make check          # 运行所有检查
make docker-up      # 启动 Docker 服务
make docker-down    # 停止 Docker 服务
make init-db        # 初始化数据库
make pre-commit     # 安装 pre-commit hooks
make pre-commit-run # 手动运行 pre-commit
make clean          # 清理缓存文件
```

## 代码规范

### 导入顺序

isort 会自动按以下顺序排序：

1. 标准库导入
2. 第三方库导入
3. 本地应用导入

示例：

```python
# 标准库
import os
from typing import Optional

# 第三方库
from fastapi import FastAPI
from sqlalchemy import Column

# 本地应用
from src.domain.agent.aggregate import Agent
from src.infrastructure.persistence.database import Base
```

### 类型注解

所有函数必须有类型注解：

```python
# ✅ 正确
def create_agent(name: str, description: str) -> Agent:
    return Agent(name=name, description=description)

# ❌ 错误（mypy 会报错）
def create_agent(name, description):
    return Agent(name=name, description=description)
```

### 行长度

最大行长度：100 字符

```python
# ✅ 正确
result = some_function(
    parameter1="value1",
    parameter2="value2",
    parameter3="value3",
)

# ❌ 错误（超过 100 字符）
result = some_function(parameter1="value1", parameter2="value2", parameter3="value3", parameter4="value4")
```

## 常见问题

### Q: pre-commit hooks 太慢怎么办？

A: 可以跳过某些 hooks：

```bash
SKIP=mypy git commit -m "your message"
```

### Q: 如何修复所有代码质量问题？

A: 运行：

```bash
make format
make check
```

### Q: mypy 报错 "Missing type hints"

A: 为所有函数添加类型注解：

```python
def my_function(param: str) -> None:
    pass
```

### Q: 如何忽略某行的 mypy 检查？

A: 使用 `# type: ignore` 注释：

```python
result = some_untyped_function()  # type: ignore
```

### Q: 如何忽略某个文件的 ruff 检查？

A: 在文件顶部添加：

```python
# ruff: noqa
```

或忽略特定规则：

```python
# ruff: noqa: E501
```
