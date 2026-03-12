# AI Agent Service - 项目架构文档

## 1. 整体架构

### 1.1 DDD分层架构

```
┌─────────────────────────────────────────────────┐
│         表现层 (Presentation Layer)              │
│         - FastAPI路由 (agents.py)                │
│         - DTO转换 (schemas.py)                   │
│         - 依赖注入 (dependencies.py)             │
└────────────────┬────────────────────────────────┘
                 │ 依赖方向：外层→内层
┌────────────────▼────────────────────────────────┐
│         应用层 (Application Layer)               │
│         - 用例 (Use Cases)                       │
│           * CreateAgentUseCase                   │
│           * ExecuteAgentTaskUseCase              │
│           * StartConversationUseCase             │
│         - 应用服务 (Application Services)        │
└────────────────┬────────────────────────────────┘
                 │ 依赖方向：外层→内层
┌────────────────▼────────────────────────────────┐
│         领域层 (Domain Layer) ⭐ 核心            │
│         - 聚合根 (Aggregates)                    │
│           * Agent                                │
│           * Conversation                         │
│         - 实体 (Entities)                        │
│           * Tool                                 │
│           * Message                              │
│         - 值对象 (Value Objects)                 │
│           * AgentId, AgentConfig                 │
│           * MessageContent                       │
│         - 仓储接口 (Repository Interfaces)       │
│           * IAgentRepository                     │
│           * IConversationRepository              │
│         - 领域服务接口 (Domain Service)          │
│           * ILLMService                          │
│         - 领域事件 (Domain Events)               │
└────────────────▲────────────────────────────────┘
                 │ 实现方向：内层←外层
┌────────────────┴────────────────────────────────┐
│         基础设施层 (Infrastructure Layer)        │
│         - 仓储实现 (AgentRepository)             │
│         - LLM服务实现 (LiteLLMService)           │
│         - 数据库 (PostgreSQL + SQLAlchemy)       │
│         - 缓存 (Redis)                           │
│         - 消息队列 (Celery)                      │
└─────────────────────────────────────────────────┘
```

### 1.2 技术栈映射

| 层次 | 技术选型 | 文件位置 |
|------|---------|---------|
| 表现层 | FastAPI + Pydantic | `src/presentation/` |
| 应用层 | Python标准库 | `src/application/` |
| 领域层 | 纯Python（无框架） | `src/domain/` |
| 基础设施层 | LangGraph + LiteLLM + SQLAlchemy + Redis | `src/infrastructure/` |

## 2. 核心领域模型

### 2.1 Agent聚合

```python
Agent (聚合根)
├── id: AgentId
├── name: str
├── description: str
├── capabilities: List[AgentCapability]
├── tools: List[Tool]  # 实体
├── config: AgentConfig  # 值对象
├── owner_id: UserId
└── is_active: bool

业务规则：
- Agent必须至少有一个能力
- 只能添加与能力匹配的工具
- 停用的Agent不能执行任务
```

### 2.2 Conversation聚合

```python
Conversation (聚合根)
├── id: ConversationId
├── agent_id: AgentId
├── user_id: UserId
├── status: ConversationStatus
└── messages: List[Message]  # 实体

业务规则：
- 关闭的对话不能添加消息
- 消息按时间顺序排列
- 支持暂停和恢复
```

## 3. 数据流

### 3.1 创建Agent流程

```
1. API请求 (表现层)
   POST /api/v1/agents/
   ↓
2. DTO验证 (表现层)
   CreateAgentRequest → CreateAgentCommand
   ↓
3. 用例执行 (应用层)
   CreateAgentUseCase.execute()
   ↓
4. 领域逻辑 (领域层)
   Agent.create() → 验证业务规则 → 发布事件
   ↓
5. 持久化 (基础设施层)
   AgentRepository.save() → PostgreSQL
   ↓
6. 返回结果 (表现层)
   CreateAgentResult → AgentResponse
```

### 3.2 执行任务流程

```
1. API请求
   POST /api/v1/agents/{id}/execute
   ↓
2. 获取聚合根 (应用层)
   AgentRepository.find_by_id()
   ↓
3. 验证状态 (领域层)
   Agent.can_execute_task()
   ↓
4. 调用LLM (基础设施层)
   LiteLLMService.execute()
   ├── LangGraph工作流编排
   ├── LiteLLM统一接口
   └── Ollama/Claude执行
   ↓
5. 返回结果
```

## 4. 依赖注入

### 4.1 依赖关系图

```
FastAPI路由
    ↓ Depends
用例 (Use Case)
    ↓ 构造函数注入
仓储接口 + 领域服务接口
    ↑ 实现
仓储实现 + 服务实现
```

### 4.2 示例代码

```python
# 表现层
@router.post("/")
async def create_agent(
    use_case: CreateAgentUseCase = Depends(get_create_agent_use_case)
):
    ...

# 依赖配置
async def get_create_agent_use_case(
    agent_repo: IAgentRepository = Depends(get_agent_repository)
) -> CreateAgentUseCase:
    return CreateAgentUseCase(agent_repo)

# 用例
class CreateAgentUseCase:
    def __init__(self, agent_repository: IAgentRepository):
        self._agent_repo = agent_repository  # 依赖接口
```

## 5. 关键设计原则

### 5.1 依赖倒置原则 (DIP)

```python
# ✅ 正确：领域层定义接口
class IAgentRepository(ABC):
    @abstractmethod
    async def save(self, agent: Agent) -> None:
        pass

# ✅ 正确：基础设施层实现接口
class AgentRepository(IAgentRepository):
    async def save(self, agent: Agent) -> None:
        # 实现细节
        ...

# ❌ 错误：领域层直接依赖实现
from infrastructure.repositories import AgentRepository  # 不要这样做
```

### 5.2 聚合边界

```python
# ✅ 正确：通过聚合根修改
agent = agent_repository.find_by_id(agent_id)
agent.add_tool(tool)  # 通过聚合根
agent_repository.save(agent)

# ❌ 错误：直接修改实体
tool = tool_repository.find_by_id(tool_id)
tool.update()  # 绕过聚合根
```

### 5.3 领域事件

```python
# 领域层发布事件
class Agent:
    def add_tool(self, tool: Tool) -> None:
        self.tools.append(tool)
        self._add_event(ToolAdded(self.id, tool.name))

# 应用层处理事件
class ToolAddedHandler:
    async def handle(self, event: ToolAdded):
        # 触发其他操作
        await notification_service.notify(event)
```

## 6. 性能优化

### 6.1 缓存策略

```python
# LLM响应缓存
cache_key = f"llm:{hash(prompt)}"
if cached := redis.get(cache_key):
    return cached

result = await llm_service.execute(...)
redis.set(cache_key, result, ttl=3600)
```

### 6.2 异步处理

```python
# 所有IO操作使用async/await
async def execute(self, command: Command) -> Result:
    agent = await self._agent_repo.find_by_id(...)  # 异步
    result = await self._llm_service.execute(...)   # 异步
    await self._agent_repo.save(...)                # 异步
```

## 7. 测试策略

### 7.1 测试金字塔

```
E2E测试 (少量)
    ↑
集成测试 (适量)
    ↑
单元测试 (大量)
```

### 7.2 测试重点

- **领域层**: 100%单元测试覆盖
- **应用层**: 用例集成测试
- **基础设施层**: 仓储集成测试
- **表现层**: API端到端测试

## 8. 部署架构

### 8.1 开发环境

```
Docker Compose
├── PostgreSQL (5432)
├── Redis (6379)
├── Ollama (11434)
└── LiteLLM (4000)

FastAPI应用 (8000)
```

### 8.2 生产环境

```
Nginx (负载均衡)
    ↓
FastAPI × 4 (多实例)
    ↓
LiteLLM (统一网关)
    ├→ Ollama集群 × 3
    └→ Claude API

PostgreSQL (主从)
Redis (集群)
```

## 9. 监控指标

- 请求QPS
- 响应时间
- LLM调用成本
- 缓存命中率
- 数据库连接池
- 错误率

## 10. 下一步扩展

1. 添加认证授权
2. 实现WebSocket流式响应
3. 添加更多Agent能力
4. 实现多Agent协作
5. 添加监控和告警
6. 性能优化和压测
