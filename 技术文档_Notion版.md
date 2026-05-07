# GoodManus 通用智能体 — 技术文档

> **版本 1.0.0 | 2026-05-01 | 项目路径 `E:\workspace\good_manus`**

GoodManus 是一个可完全私有部署的 AI Agent 系统。采用 Planner-ReAct 双智能体协作架构，自动将用户任务分解为子步骤，在 Docker 沙箱中执行文件操作、Shell 命令、浏览器操控、网页搜索、代码编写。通过 MCP 和 A2A 协议扩展外部工具与远程 Agent。

> 架构全景图请查看同目录下的 `architecture.html`（浏览器打开）或 `architecture.svg`（直接拖入 Notion）。

---

# 一、项目总览

## 技术栈速览

| 层级 | 技术 | 说明 |
|:---|:---|:---|
| 后端框架 | FastAPI ≥0.135 | 异步 Python Web 框架 |
| 前端框架 | Next.js (TypeScript) | App Router + React |
| 数据库 | PostgreSQL 16 | 会话、文件、记忆持久化 |
| 缓存/队列 | Redis 7.2 | Task 流、缓存、消息队列 |
| 对象存储 | 腾讯云 COS | 文件上传/下载 |
| LLM | DeepSeek v4-pro | OpenAI 兼容协议 |
| 浏览器 | Playwright ≥1.58 | 自动化操控 |
| 沙箱 | Docker (Ubuntu 22.04) | 代码执行隔离环境 |
| 协议 | MCP + A2A | 外部工具与 Agent 互操作 |
| 网关 | Nginx Alpine | 反向代理 + 静态资源 |
| 编排 | Docker Compose | 6 服务 + bridge 网络 |

## 项目目录

```
good_manus/
├── api/                         #   FastAPI 后端
│   ├── app/
│   │   ├── domain/              # 领域层：模型、Agent、Flow、工具、协议
│   │   ├── application/         # 应用层：AgentService 等业务编排
│   │   ├── infrastructure/      # 基础设施：PostgreSQL、Redis、LLM 实现
│   │   └── interfaces/          # 接口层：路由、Schema、异常处理
│   ├── core/config.py           # 环境变量加载（Pydantic Settings）
│   ├── config.yaml              # 运行时配置（LLM、MCP、A2A）
│   └── main.py                  # 应用入口 + 生命周期管理
│
├── sandbox/                     #   沙箱微服务（独立容器）
│   └── app/endpoints/           # File / Shell / Supervisor API
│
├── ui/                          #   Next.js 前端
│   ├── app/page.tsx             # 首页
│   └── app/sessions/[id]/       # 会话详情页
│
├── nginx/                       # Nginx 配置
├── docker-compose.yml           # 容器编排
├── architecture.html            # 系统架构图
└── architecture.svg             # 架构图 SVG（Notion 直接上传）
```

---

# 二、架构设计

## 2.1 Clean Architecture 四层分离

GoodManus 后端严格遵循整洁架构，依赖方向始终向内：

> **接口层** → 接收 HTTP 请求，参数校验，返回响应
> **应用层** → 编排领域对象，无业务逻辑，纯流程控制
> **领域层** → 核心业务模型、Agent 逻辑、工具协议（零外部依赖）
> **基础设施层** → 数据库实现、LLM 调用、外部 API（实现领域层定义的协议）

>   **依赖规则：** 上层可以依赖下层，下层决不能依赖上层。领域层不导入 FastAPI、SQLAlchemy 等任何框架。

## 2.2 多智能体协作流程

Planner-ReAct 双 Agent 模式：

1. **PlannerAgent** 分析用户消息 → 拆解任务为 Plan（多个 Step）
2. **ReActAgent** 逐个执行 Step，每个 Step 内循环：Think → Tool Call → Observe
3. 每个 Step 完成后，**PlannerAgent** 根据结果更新 Plan
4. 所有 Step 完成后，**ReActAgent** 汇总生成最终回复

## 2.3 Flow 状态机

| 状态 | 含义 | 下一个状态 |
|:---|:---|:---|
| `IDLE` | 空闲，等待任务 | → `PLANNING` |
| `PLANNING` | PlannerAgent 创建 Plan | → `EXECUTING` |
| `EXECUTING` | ReActAgent 执行当前 Step | → `UPDATING`（Step 完成）或 `SUMMARIZING`（全部完成） |
| `UPDATING` | PlannerAgent 更新 Plan | → `EXECUTING` |
| `SUMMARIZING` | ReActAgent 生成总结 | → `COMPLETED` |
| `COMPLETED` | 任务终结 | → `IDLE` |

---

# 三、API 接口设计

> 所有接口统一前缀 `/api`，统一响应格式 `{code, msg, data}`

## 3.1 路由分组

| 路由前缀 | 模块 | 核心功能 |
|:---|:---|:---|
| `/api/status` | 状态 | 系统健康检查（PostgreSQL + Redis + FastAPI） |
| `/api/sessions` | 会话 | 创建/列表/详情/删除 + 聊天 SSE + VNC WebSocket |
| `/api/files` | 文件 | 上传/下载/信息查询 |
| `/api/app-config` | 设置 | LLM/Agent/MCP/A2A 配置管理 |

## 3.2 核心接口：POST /api/sessions/{id}/chat

这是整个系统的核心——通过 SSE 流式推送 Agent 执行过程中的所有事件。

**请求体：**

```json
{
  "message": "帮我写一个 Flask Hello World 应用",
  "attachments": ["file_id_1"],
  "event_id": null,
  "timestamp": 1714567890
}
```

**SSE 事件类型：**

| 事件 | 触发时机 | 关键字段 |
|:---|:---|:---|
| `message` | 用户发言 / AI 回复 | `role`, `message`, `attachments` |
| `title` | 会话标题生成 | `title` |
| `plan` | 计划创建/更新/完成 | `steps[]` 含 `id`, `description`, `status` |
| `step` | 子步骤状态变化 | `id`, `description`, `status` |
| `tool` | 工具调用中/已完成 | `tool_call_id`, `name`, `function`, `args`, `content` |
| `done` | 全部任务完成 | — |
| `error` | 异常 | `error` |
| `wait` | 等待用户输入 | — |

## 3.3 会话模块全部接口

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| `POST` | `/sessions` | 创建新会话 |
| `GET` | `/sessions` | 获取会话列表 |
| `POST` | `/sessions/stream` | SSE 流式推送会话列表（5 秒间隔） |
| `GET` | `/sessions/{id}` | 获取会话详情 + 事件历史 |
| `POST` | `/sessions/{id}/chat` | **发起聊天（SSE 流式）** |
| `POST` | `/sessions/{id}/stop` | 停止会话 |
| `POST` | `/sessions/{id}/delete` | 删除会话 |
| `POST` | `/sessions/{id}/clear-unread-message-count` | 清除未读 |
| `GET` | `/sessions/{id}/files` | 会话关联文件列表 |
| `POST` | `/sessions/{id}/file` | 读取沙箱文件内容 |
| `POST` | `/sessions/{id}/shell` | 读取 Shell 会话输出 |
| `WS` | `/sessions/{id}/vnc` | VNC 远程桌面（双向转发） |

## 3.4 设置模块全部接口

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| `GET/POST` | `/app-config/llm` | 获取/更新 LLM 配置（隐藏 api_key） |
| `GET/POST` | `/app-config/agent` | 获取/更新 Agent 参数 |
| `GET/POST` | `/app-config/mcp-servers` | 获取/新增 MCP 服务 |
| `POST` | `/app-config/mcp-servers/{name}/delete` | 删除 MCP 服务 |
| `POST` | `/app-config/mcp-servers/{name}/enabled` | 启用/禁用 MCP 服务 |
| `GET/POST` | `/app-config/a2a-servers` | 获取/新增 A2A 服务 |
| `POST` | `/app-config/a2a-servers/{id}/delete` | 删除 A2A 服务 |
| `POST` | `/app-config/a2a-servers/{id}/enabled` | 启用/禁用 A2A 服务 |

## 3.5 文件模块全部接口

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| `POST` | `/files` | 上传文件（multipart/form-data）→ 存入 COS + 沙箱 |
| `GET` | `/files/{id}` | 获取文件元信息 |
| `GET` | `/files/{id}/download` | 流式下载文件 |

---

# 四、领域模型

## 4.1 Session（会话）

会话是用户与 Agent 交互的基本单元，状态包括 `PENDING` → `RUNNING` → `WAITING` / `COMPLETED`。

核心字段：

- `sandbox_id` — 关联的 Docker 沙箱
- `task_id` — 关联的异步 Task（Redis Stream 驱动）
- `events[]` — 事件历史（JSONB 存储）
- `memories{}` — 两个 Agent（planner / react）各自的对话记忆
- `files[]` — 关联文件列表

## 4.2 Plan & Step（计划与步骤）

```
Plan
├── title       → "Flask Hello World 应用开发"
├── goal        → "创建一个可运行的 Flask 应用"
├── language    → "中文"
└── steps[]
    ├── Step(id="a1", description="创建项目目录结构")
    ├── Step(id="a2", description="编写 Flask 应用代码")
    └── Step(id="a3", description="编写 Dockerfile")
```

每个 Step 执行后记录 `success`、`result`、`attachments`，失败时记录 `error`。

## 4.3 Event 事件系统

所有 Agent 输出都通过异步生成器流式产生事件：

| 事件类 | 用途 |
|:---|:---|
| `MessageEvent` | 用户/AI 对话消息 |
| `TitleEvent` | 会话标题（PlannerAgent 生成） |
| `PlanEvent` | 计划创建/更新/完成 |
| `StepEvent` | 子步骤开始/完成/失败 |
| `ToolEvent` | 工具调用状态（CALLING / CALLED） |
| `DoneEvent` | 任务结束 |
| `ErrorEvent` | 错误信息 |
| `WaitEvent` | 暂停等待用户输入 |

> `EventMapper` 类通过 Python 运行时反射，自动将领域 Event 转换为 SSE 流式事件格式。新增事件类型无需修改映射逻辑。

## 4.4 Memory（记忆管理）

每个 Agent 独立维护一份 `Memory`：

- `messages[]` — OpenAI 格式的消息列表（role + content + tool_calls）
- `max_messages` — 触发压缩的阈值
- `summary` — 压缩后的摘要

> 记忆压缩策略：保留 system prompt + 最近 N 条消息，其余压缩为摘要文本。每完成一个 Step 自动调用 `compact_memory()` 防止上下文腐化。

---

# 五、Agent 多智能体系统

## 5.1 BaseAgent 基类

位置：`api/app/domain/services/agents/base.py`（272 行，系统最核心文件）

封装了与 LLM 交互、工具调用、记忆管理的通用逻辑。

**核心调用链：**

```python
invoke(query)
  → _invoke_llm(messages)         # 调用 LLM + 自动重试
      → _add_to_memory()          # 消息持久化
      → llm.invoke()              # OpenAI 兼容协议
  → for _ in range(max_iterations):
      → _get_tool(name)           # 查找工具实例
      → yield ToolEvent(CALLING)  # 通知前端："即将调用工具"
      → _invoke_tool(tool, args)  # 执行工具 + 重试
      → yield ToolEvent(CALLED)   # 通知前端："工具执行完成"
      → _invoke_llm(results)      # 工具结果回传 LLM 继续推理
```

**关键设计：**

1. 每次只允许调用 **1 个工具**——防止 LLM 并行调用导致状态混乱
2. LLM 返回空内容 → 自动注入 "AI无响应内容，请继续" 重试
3. 兼容 DeepSeek 思考模型的 `reasoning_content` 字段
4. 工具调用失败不抛异常，将错误作为 `ToolResult(success=False)` 返回给 LLM 自行处理

## 5.2 PlannerAgent（规划智能体）

```python
name = "planner"
format = "json_object"     # 强制 JSON 输出
tool_choice = "none"       # 禁用工具，纯文本推理
```

**两个方法：**

`create_plan(message)` — 将用户消息转换为结构化 Plan
- 输出 `{title, goal, language, steps: [{id, description}], message}`
- 自带归一化逻辑：处理 LLM 返回字符串列表（而非对象列表）的边界情况

`update_plan(plan, completed_step)` — 根据已完成的步骤刷新 Plan
- 保留旧 Plan 中已完成的步骤
- 用 LLM 返回的新步骤替换未完成部分

## 5.3 ReActAgent（执行智能体）

```python
name = "react"
format = "json_object"     # 不限制 tool_choice，允许工具调用
```

**三个方法：**

`execute_step(plan, step, message)` — 执行单个子步骤
- 进入 ReAct 循环：Think → Tool Call → Observe
- 如果工具是 `message_ask_user` → 产出 `WaitEvent`，等待用户输入后继续
- 步骤完成 → 解析 JSON 结果（success, result, attachments）

`summarize()` — 所有步骤完成后汇总
- 生成最终自然语言回复 + 产出附件列表

## 5.4 PlannerReActFlow（编排器）

位置：`api/app/domain/services/flows/planner_react.py`（213 行）

> 这是整个系统的「大脑」——通过状态机协调 PlannerAgent 和 ReActAgent。

流程伪代码：

```
IDLE → PLANNING
  → PlannerAgent.create_plan(message)
  → EXECUTING
    → for each step:
        → ReActAgent.execute_step(plan, step)
        → compact_memory()
        → UPDATING
          → PlannerAgent.update_plan(plan, step)
          → EXECUTING
  → SUMMARIZING
    → ReActAgent.summarize()
  → COMPLETED → IDLE
```

---

# 六、工具系统

## 6.1 架构

所有工具继承 `BaseTool`，通过 `@tool` 装饰器注册：

```python
class FileTool(BaseTool):
    name = "file"

    @tool(name="file_read", description="读取文件", parameters={...})
    async def file_read(self, filepath: str, ...) -> ToolResult:
        return await self.sandbox.file_read(filepath, ...)
```

`@tool` 装饰器自动提取函数签名 + 注解，生成 OpenAI function calling 格式的 Schema。

## 6.2 内置工具一览

| 工具箱 | 工具列表 | 依赖 |
|:---|:---|:---|
| **FileTool** | `file_read`、`file_write`、`file_str_replace`、`file_find_in_content`、`file_find_by_name`、`file_list` | Sandbox |
| **ShellTool** | `shell_exec`、`shell_read`、`shell_wait`、`shell_write`、`shell_kill` | Sandbox |
| **BrowserTool** | `browser_navigate`、`browser_click`、`browser_screenshot` | Playwright |
| **SearchTool** | `web_search` | Bing API |
| **MessageTool** | `message_ask_user` | — |
| **MCPTool** | 动态（取决于连接的 MCP 服务器） | MCP 协议 |
| **A2ATool** | `get_remote_agent_cards`、`call_remote_agent` | A2A 协议 |

## 6.3 MCP 客户端管理器

位置：`api/app/domain/services/tools/mcp.py`（390 行）

**支持的传输协议：**

| 协议 | 场景 |
|:---|:---|
| `stdio` | 本地命令行 MCP 服务 |
| `sse` | HTTP SSE 长连接 |
| `streamable_http` | HTTP Streaming（项目主要使用，如 Jina AI） |

**连接流程：**

```
initialize()
  → for each server in config:
      → _connect_{transport}_server(name, config)
          → AsyncExitStack.enter_async_context(transport)
          → ClientSession(read, write)
          → session.initialize()
          → session.list_tools()  ← 缓存工具 Schema
```

**工具命名隔离：**

MCP 工具暴露给 LLM 时统一重命名为 `mcp_{server_name}_{tool_name}` 格式。例如 Jina AI 的搜索工具 → `mcp_jina-mcp-server_search`。

**资源清理：**

`cleanup()` 方法幂等安全，使用 AsyncExitStack 统一管理所有上下文。特别注意了 anyio cancel scope 在不同 Task 中退出的边界情况。

## 6.4 A2A 客户端管理器

位置：`api/app/domain/services/tools/a2a.py`（223 行）

通过 `httpx.AsyncClient` 与远程 Agent 通信：

```
initialize()
  → for each a2a server:
      → GET {base_url}/.well-known/agent-card.json
      → 缓存 agent_cards[id]

invoke(agent_id, query)
  → POST {url} with JSON-RPC 2.0 message/send
  → 返回远程 Agent 的执行结果
```

---

# 七、基础设施

## 7.1 数据库（PostgreSQL 16）

| 表 | 核心字段 | 说明 |
|:---|:---|:---|
| `sessions` | id, sandbox_id, task_id, title, status, events(JSONB), files(JSONB), memories(JSONB) | 会话主表 |
| `files` | id, session_id, filename, filepath, mime_type, size, cos_key | 文件记录表 |

迁移工具：Alembic，共 4 个迁移版本。

## 7.2 Redis（7.2）

| 用途 | 实现 |
|:---|:---|
| Task 输入/输出流 | `RedisStreamTask` — Agent 事件队列 |
| 消息队列 | `RedisStreamMessageQueue` |
| 缓存 | 会话状态、配置 |

## 7.3 Docker 沙箱

`DockerSandbox` 管理容器的完整生命周期：

- **创建** — Ubuntu 22.04 + Chrome + Python 3.10 + Node.js 20
- **文件操作** — 通过沙箱内 File API 代理
- **Shell 执行** — 通过沙箱内 Shell API（支持 pty + 长进程管理）
- **浏览器** — 通过 Playwright CDP 协议操控沙箱内 Chrome
- **VNC** — noVNC 远程桌面
- **TTL** — 默认 60 分钟自动回收

## 7.4 LLM 调用

`LLM` Protocol 定义统一接口，`OpenAILLM` 实现通过 OpenAI SDK 调用 DeepSeek：

```python
class LLM(Protocol):
    async def invoke(
        self,
        messages: List[Dict],             # OpenAI 格式
        tools: List[Dict] = None,         # function calling Schema
        response_format: Dict = None,     # json_object 等
        tool_choice: str = None,          # auto / none
    ) -> Dict:
        ...
```

## 7.5 健康检查

`StatusService.check_all()` 在应用启动和 `/api/status` 请求时检测 PostgreSQL（pg_isready）、Redis（PING）、FastAPI 自身状态。

---

# 八、部署架构

## 8.1 Docker Compose 服务启动顺序

```
1. manus-redis     → 健康检查通过
2. manus-postgres  → 健康检查通过
3. manus-sandbox   → 镜像构建
4. manus-api       → 依赖 Redis + PostgreSQL 健康
5. manus-ui        → 依赖 API 健康
6. manus-nginx     → 依赖 UI + API 健康，暴露 :8088
```

全部服务通过 `manus-network` bridge 网络通信。

## 8.2 关键配置项

**config.yaml — 运行时配置：**

```yaml
llm_config:
  base_url: https://api.deepseek.com/
  model_name: deepseek-v4-pro
  temperature: 0.7
  max_tokens: 8192

agent_config:
  max_iterations: 100
  max_retries: 3
  max_search_results: 10
```

**.env — 环境变量（部分）：**

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_HOST=localhost
SANDBOX_ADDRESS=http://manus-sandbox:8000
SANDBOX_TTL_MINUTES=60
```

---

# 九、关键设计模式总结

| 模式 | 应用位置 |
|:---|:---|
| **Clean Architecture** | 整体 4 层分离，依赖倒置 |
| **Protocol（接口协议）** | `domain/external/` — LLM、Sandbox、Browser 等 |
| **Repository + UoW** | `domain/repositories/` — 数据访问抽象 |
| **State Machine** | `PlannerReActFlow.status` — 6 状态流转 |
| **AsyncGenerator** | 所有 Agent invoke — 流式事件推送 |
| **Template Method** | `BaseAgent.invoke()` — 骨架 + 子类覆写 Prompt |
| **Decorator** | `@tool` — 方法自动注册为工具 |
| **Strategy** | MCP 三种传输协议选择 |
| **Observer** | SSE Event → 前端订阅 |
| **Singleton** | `@lru_cache()` on `get_settings()` |

---

# 十、核心脚本速查

| 文件 | 行数 | 职责 |
|:---|:---|:---|
| `api/app/main.py` | 99 | 应用入口：lifespan 管理、数据库迁移、中间件注册 |
| `api/core/config.py` | 65 | Pydantic Settings 加载 .env + 环境变量 |
| `api/app/domain/services/agents/base.py` | 272 | Agent 基类：LLM 调用、工具执行、记忆管理 |
| `api/app/domain/services/agents/planner.py` | 151 | 规划智能体：任务分解 + 计划更新 |
| `api/app/domain/services/agents/react.py` | 145 | 执行智能体：ReAct 循环 + 总结 |
| `api/app/domain/services/flows/planner_react.py` | 213 | 编排器：6 状态机协调双 Agent |
| `api/app/domain/services/tools/mcp.py` | 390 | MCP 客户端管理器：3 种传输协议 |
| `api/app/domain/services/tools/a2a.py` | 223 | A2A 客户端管理器：Agent Card + JSON-RPC |
| `api/app/domain/services/tools/tool.py` | 216 | FileTool：6 个文件操作工具 |
| `api/app/application/services/agent_service.py` | 259 | AgentService：Task 创建、SSE 流式推送 |
| `api/app/interfaces/schemas/event.py` | 303 | Event 映射器：领域事件 → SSE 流式事件 |
| `api/app/interfaces/endpoints/session_routes.py` | 354 | 会话路由：11 个端点 + VNC WebSocket |

---

> **文档维护：** Roxy（洛琪希）| **生成：** 2026-05-01 | **配套文件：** `architecture.html` · `architecture.svg`
