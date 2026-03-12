# AI Agent Service - DDD架构

基于领域驱动设计（DDD）的 AI 代理网关服务，为用户提供统一的大模型访问接口。

## 🎯 核心功能

### 统一模型接入
- **本地模型支持**：通过 Ollama 接入本地推理模型（Qwen、Llama 等）
- **闭源 API 支持**：接入 Claude、GPT-4 等闭源大模型 API
- **透明路由**：自动模型选择和故障转移机制

### 用户系统
- **注册登录**：用户注册和身份认证
- **令牌管理**：创建和管理 API 令牌
- **使用追踪**：记录 API 调用次数和使用量

### 无感调用
用户只需一个令牌，即可通过统一接口调用任意模型，无需关心底层实现细节。

## 架构设计

### DDD分层架构

```
表现层 (Presentation)
    ↓ 依赖
应用层 (Application)
    ↓ 依赖
领域层 (Domain) ⭐ 核心
    ↑ 实现
基础设施层 (Infrastructure)
```

### 技术栈

- **Web框架**: FastAPI + Uvicorn
- **代理框架**: LangGraph
- **LLM网关**: LiteLLM（统一本地和云端模型）
- **本地推理**: Ollama
- **数据库**: PostgreSQL + pgvector
- **缓存**: Redis
- **任务队列**: Celery

## 快速开始

### 方式一：使用自动化脚本

```bash
# 运行快速开始脚本
bash scripts/setup.sh
```

### 方式二：手动设置

#### 1. 环境准备

```bash
# 克隆项目
cd ai-proxy-service

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
pip install -e ".[dev]"

# 安装 pre-commit hooks
make pre-commit
```

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
# 特别注意配置 ANTHROPIC_API_KEY（如果使用 Claude）
```

#### 3. 启动基础设施

```bash
# 使用 Makefile
make docker-up

# 或手动启动
cd docker
docker-compose up -d
```

这将启动：
- PostgreSQL (端口 5432)
- Redis (端口 6379)
- Ollama (端口 11434)
- LiteLLM (端口 4000)

#### 4. 初始化数据库

```bash
# 使用 Makefile
make init-db

# 或手动运行
# 创建数据库表
python scripts/init_db.py
```

#### 5. 下载本地模型

```bash
# 下载Qwen模型
docker exec -it ai-proxy-ollama ollama pull qwen2.5:14b

# 或下载Llama模型
docker exec -it ai-proxy-ollama ollama pull llama3.2
```

#### 6. 启动应用

```bash
# 开发模式
uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn src.presentation.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 7. 访问API文档

打开浏览器访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API使用示例

### 创建Agent

```bash
curl -X POST "http://localhost:8000/api/v1/agents/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "代码助手",
    "description": "帮助编写和审查代码",
    "capabilities": ["code_generation", "text_generation"]
  }'
```

### 执行任务

```bash
curl -X POST "http://localhost:8000/api/v1/agents/{agent_id}/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "编写一个Python函数计算斐波那契数列"
  }'
```

## 项目结构

```
ai-proxy-service/
├── src/
│   ├── presentation/      # 表现层：FastAPI路由、DTO
│   ├── application/       # 应用层：用例、应用服务
│   ├── domain/           # 领域层：聚合根、实体、值对象
│   └── infrastructure/   # 基础设施层：仓储实现、LLM服务
├── tests/                # 测试
├── docker/              # Docker配置
└── scripts/             # 工具脚本
```

## DDD核心概念

### 聚合根 (Aggregate Root)

- **Agent**: 代理聚合根，管理代理的生命周期和能力
- **Conversation**: 对话聚合根，管理对话和消息历史

### 值对象 (Value Object)

- `AgentId`, `ConversationId`: 实体标识
- `AgentConfig`: 代理配置
- `MessageContent`: 消息内容

### 仓储接口 (Repository Interface)

- 领域层定义接口
- 基础设施层实现接口
- 通过依赖注入使用

### 领域服务 (Domain Service)

- `ILLMService`: LLM执行服务接口

## 开发指南

### 添加新功能

1. **领域层**: 定义聚合根、实体、值对象
2. **应用层**: 创建用例
3. **基础设施层**: 实现仓储和服务
4. **表现层**: 添加API路由

### 运行测试

```bash
# 使用 Makefile
make test           # 运行所有测试
make test-cov       # 运行测试并生成覆盖率报告

# 或手动运行
# 单元测试
pytest tests/unit

# 集成测试
pytest tests/integration

# 所有测试
pytest
```

### 代码质量检查

```bash
# 使用 Makefile（推荐）
make format         # 自动格式化代码（autoflake + isort + black）
make lint           # 代码检查（ruff）
make type-check     # 类型检查（mypy）
make check          # 运行所有检查

# 或手动运行
autoflake --in-place --remove-all-unused-imports --remove-unused-variables -r src/ tests/
isort src/ tests/
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Pre-commit Hooks

```bash
# 安装 pre-commit hooks
make pre-commit

# 手动运行所有 hooks
pre-commit run --all-files
```

安装后，每次 commit 前会自动运行：
- autoflake：移除未使用的导入和变量
- isort：排序导入
- black：格式化代码
- ruff：代码检查
- mypy：类型检查
- 基础检查：尾随空格、文件结尾、YAML/JSON 验证等

## 性能预估

### 本地模型（Ollama）
- 单GPU (RTX 4090): 2-3 QPS
- 日处理量: ~17万请求

### 混合模式（本地 + Claude）
- 总QPS: 12-23
- 日处理量: ~100万请求

## 监控

- Prometheus指标: http://localhost:9090
- 应用日志: logs/app.log

## 许可证

MIT License
