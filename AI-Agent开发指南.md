# GoodManus AI Agent 全栈项目 - 企业级技术文档

## 文档目标

本文档专为算法工程师转型AI Agent开发岗位设计，涵盖：
1. 前后端开发核心概念与模式
2. 项目架构与技术栈详解
3. 接口与路由设计原理
4. 与Claude协作开发的工作流程
5. AI Agent面试核心知识点

---

## 第一部分：基础概念篇

### 1.1 什么是API？

**API (Application Programming Interface)** 是应用程序之间通信的桥梁。

**类比理解：**
- 餐厅点餐：你是客户端，厨房是服务端，服务员就是API
- 你不需要知道厨房怎么做饭，只需要通过服务员（API）点餐和取餐

**代码示例：**
```python
# 后端：提供API（厨房做菜）
from fastapi import FastAPI

app = FastAPI()

@app.get("/menu")  # API端点：获取菜单
def get_menu():
    return {"items": ["红烧肉", "清蒸鱼"]}

@app.post("/order")  # API端点：下单
def create_order(item: str):
    return {"message": f"已下单: {item}"}
```

```typescript
// 前端：调用API（顾客点餐）
const response = await fetch("/api/menu");
const menu = await response.json();
// menu = { items: ["红烧肉", "清蒸鱼"] }
```

### 1.2 什么是路由(Route)？

**路由**是URL路径与处理函数的映射关系。

**类比理解：**
- 路由器决定数据包的去向
- Web路由决定不同URL由哪个函数处理

**代码示例：**
```python
from fastapi import APIRouter

router = APIRouter(prefix="/sessions", tags=["会话模块"])

# 路由：GET /sessions -> 获取所有会话
@router.get("")
async def get_all_sessions():
    return {"sessions": []}

# 路由：POST /sessions -> 创建新会话
@router.post("")
async def create_session():
    return {"session_id": "123"}

# 路由：GET /sessions/{id} -> 获取指定会话
@router.get("/{session_id}")
async def get_session(session_id: str):
    return {"session_id": session_id}
```

**路由设计原则：**
| HTTP方法 | 用途 | 示例 |
|---------|------|------|
| GET | 获取数据 | `GET /sessions` 获取会话列表 |
| POST | 创建资源 | `POST /sessions` 创建新会话 |
| PUT | 更新资源 | `PUT /sessions/123` 更新会话 |
| DELETE | 删除资源 | `DELETE /sessions/123` 删除会话 |

### 1.3 什么是前后端分离？

**架构图：**
```
┌─────────────┐      HTTP请求      ┌─────────────┐
│   前端 UI   │ <────────────────> │   后端 API  │
│  (Next.js)  │   JSON数据交换      │  (FastAPI)  │
└─────────────┘                    └──────┬──────┘
     │                                    │
     │  负责：                             │  负责：
     │  - 页面展示                         │  - 业务逻辑
     │  - 用户交互                         │  - 数据存储
     │  - 调用API                          │  - AI Agent
     └────────────────────────────────────┘
```

**为什么分离？**
1. **职责清晰**：前端专注UI，后端专注业务
2. **技术独立**：可以分别升级技术栈
3. **团队协作**：前后端可以并行开发
4. **多端复用**：一套API支持Web、App、小程序

---

## 第二部分：项目架构篇

### 2.1 整体架构

```
GoodManus AI Agent 系统
├── 前端层 (Next.js + React)
│   ├── 页面路由 (App Router)
│   ├── 组件系统 (Shadcn UI)
│   ├── API客户端 (封装fetch)
│   └── 状态管理 (React Hooks)
│
├── 网关层 (Nginx)
│   ├── 反向代理
│   ├── 负载均衡
│   └── 静态资源服务
│
├── 后端层 (FastAPI + Python)
│   ├── 接口层 (Interfaces)
│   ├── 应用层 (Application)
│   ├── 领域层 (Domain)
│   └── 基础设施层 (Infrastructure)
│
├── AI Agent层
│   ├── LLM调用 (DeepSeek)
│   ├── MCP协议支持
│   ├── A2A协议支持
│   └── 工具调用系统
│
└── 数据层
    ├── PostgreSQL (持久化数据)
    ├── Redis (缓存/消息队列)
    └── 沙箱环境 (代码执行)
```

### 2.2 后端分层架构详解

本项目采用**领域驱动设计(DDD)**的分层架构：

```
┌─────────────────────────────────────┐
│         接口层 (Interfaces)          │  <- HTTP请求入口
│  - routes: 路由定义                   │
│  - schemas: 数据校验                  │
│  - middleware: 中间件                 │
├─────────────────────────────────────┤
│        应用层 (Application)           │  <- 业务编排
│  - services: 应用服务                 │
│  - errors: 异常定义                   │
├─────────────────────────────────────┤
│         领域层 (Domain)               │  <- 核心业务
│  - models: 领域模型                   │
│  - repositories: 仓储接口             │
│  - services: 领域服务                 │
├─────────────────────────────────────┤
│      基础设施层 (Infrastructure)       │  <- 技术实现
│  - storage: 数据库/缓存实现            │
│  - external: 外部服务调用              │
│  - logging: 日志系统                  │
└─────────────────────────────────────┘
```

**分层职责说明：**

| 层级 | 职责 | 举例 |
|-----|------|------|
| 接口层 | 接收请求、返回响应、参数校验 | FastAPI路由、Pydantic模型 |
| 应用层 | 编排领域对象、协调多个领域服务 | AgentService、SessionService |
| 领域层 | 核心业务逻辑、业务规则 | Session模型、Event模型 |
| 基础设施层 | 数据持久化、外部API调用 | PostgreSQL、Redis、LLM API |

**依赖规则：** 上层可以调用下层，下层不能调用上层。

### 2.3 前端架构详解

```
ui/
├── app/                    # Next.js App Router
│   ├── page.tsx           # 首页（创建会话）
│   ├── layout.tsx         # 根布局
│   └── sessions/          # 会话详情页
│       └── [id]/
│           └── page.tsx
│
├── components/            # React组件
│   ├── chat-header.tsx   # 聊天头部
│   ├── chat-input.tsx    # 输入框
│   └── ui/               # 基础UI组件
│
├── lib/                   # 工具库
│   ├── api/              # API封装
│   │   ├── session.ts    # 会话API
│   │   ├── types.ts      # TypeScript类型
│   │   └── fetch.ts      # 请求封装
│   └── utils.ts          # 通用工具
│
├── hooks/                 # 自定义Hooks
├── providers/             # Context Providers
└── config/                # 配置文件
```

---

## 第三部分：核心流程详解

### 3.1 用户创建会话流程

```
用户操作                    前端                        后端
   │                        │                          │
   │  输入问题，点击发送      │                          │
   ├───────────────────────>|                          │
   │                        │  1. POST /sessions       │
   │                        │  (创建会话)               │
   │                        ├─────────────────────────>|  SessionService
   │                        │                          │  .create_session()
   │                        │  2. 返回 session_id      │
   │                        │<─────────────────────────┤
   │                        │                          │
   │                        │  3. 跳转到 /sessions/123 │
   │                        │  (携带消息数据)           │
   │                        │                          │
   │                        │  4. POST /sessions/123/chat
   │                        │  (发送消息)               │
   │                        ├─────────────────────────>|  AgentService
   │                        │                          │  .chat()
   │                        │  5. SSE流式返回          │
   │                        │<─────────────────────────│
   │  实时看到AI回复          │                          │
   │<───────────────────────│                          │
```

### 3.2 AI Agent处理流程

```
用户消息
    │
    ▼
┌─────────────┐
│  Agent服务   │<──── 从配置加载LLM、MCP、A2A配置
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  记忆检索    │<──── 查询相关历史消息
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  LLM调用    │<──── 发送prompt给DeepSeek API
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  意图识别    │
└──────┬──────┘
       │
       ├──────────┬──────────┬──────────┐
       ▼          ▼          ▼          ▼
   直接回答    调用工具    需要规划   请求确认
       │          │          │          │
       ▼          ▼          ▼          ▼
   生成回复   执行MCP/    创建Plan   等待用户
   流式返回   内置工具    分步执行   输入
```

---

## 第四部分：关键技术详解

### 4.1 FastAPI核心概念

**什么是FastAPI？**
FastAPI是一个现代、快速（高性能）的Python Web框架，基于Starlette和Pydantic。

**核心特性：**
```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI()

# 1. 自动数据校验 (Pydantic)
class UserRequest(BaseModel):
    name: str
    age: int

# 2. 依赖注入系统
async def get_db():
    db = create_connection()
    try:
        yield db
    finally:
        db.close()

# 3. 自动API文档
@app.post("/users")
async def create_user(
    request: UserRequest,
    db: Database = Depends(get_db)  # 依赖注入
):
    """创建用户
    
    - 自动校验request参数
    - 自动注入db连接
    - 自动生成API文档
    """
    return {"user_id": db.insert(request)}
```

**依赖注入的好处：**
1. 解耦：服务不直接创建依赖
2. 测试：可以轻松mock依赖
3. 复用：同一依赖可在多个路由使用
4. 生命周期管理：自动处理资源释放

### 4.2 SSE (Server-Sent Events)

**什么是SSE？**
服务端向客户端推送实时数据的技术，适合AI流式回复场景。

**为什么用SSE而不是WebSocket？**
| 特性 | SSE | WebSocket |
|-----|-----|-----------|
| 方向 | 服务端→客户端单向 | 双向通信 |
| 复杂度 | 简单（HTTP） | 需要升级协议 |
| 重连 | 浏览器自动处理 | 需手动实现 |
| AI场景 | 适合（只需要推送） | 过度设计 |

**代码示例：**
```python
# 后端：FastAPI SSE
from sse_starlette import EventSourceResponse

async def event_generator():
    async for chunk in llm.stream_generate(prompt):
        yield {
            "event": "message",
            "data": json.dumps({"content": chunk})
        }

@app.post("/chat")
async def chat():
    return EventSourceResponse(event_generator())
```

```typescript
// 前端：接收SSE
const eventSource = new EventSource('/api/sessions/123/chat');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  appendMessage(data.content);  // 实时追加消息
};

eventSource.onerror = () => {
  eventSource.close();
};
```

### 4.3 WebSocket (VNC连接)

**WebSocket用途：**
- VNC远程桌面需要双向实时通信
- 键盘/鼠标事件：客户端→服务端
- 屏幕画面：服务端→客户端

**代码示例：**
```python
@app.websocket("/{session_id}/vnc")
async def vnc_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    # 连接到沙箱VNC服务
    async with websockets.connect(vnc_url) as sandbox_ws:
        # 双向转发
        async def forward_to_sandbox():
            while True:
                data = await websocket.receive_bytes()
                await sandbox_ws.send(data)
        
        async def forward_from_sandbox():
            while True:
                data = await sandbox_ws.recv()
                await websocket.send_bytes(data)
        
        # 并行运行两个转发任务
        await asyncio.gather(
            forward_to_sandbox(),
            forward_from_sandbox()
        )
```

### 4.4 MCP (Model Context Protocol)

**什么是MCP？**
MCP是Anthropic提出的开放协议，用于标准化AI模型与外部工具的连接。

**MCP架构：**
```
┌─────────────┐        MCP协议         ┌─────────────┐
│   AI Agent  │<─────────────────────>│  MCP服务器  │
│  (Client)   │   标准化工具调用格式    │  (Server)   │
└─────────────┘                       └──────┬──────┘
                                             │
                                    ┌────────┴────────┐
                                    ▼                 ▼
                              ┌──────────┐      ┌──────────┐
                              │ 高德地图  │      │ Jina AI  │
                              │  服务    │      │  服务    │
                              └──────────┘      └──────────┘
```

**配置示例：**
```yaml
mcp_config:
  mcpServers:
    jina-mcp-server:
      transport: streamable_http
      enabled: true
      url: https://mcp.jina.ai/v1
      headers:
        Authorization: Bearer xxx
```

### 4.5 A2A (Agent-to-Agent)

**什么是A2A？**
Google提出的协议，用于Agent之间的协作通信。

**与MCP的区别：**
| 协议 | 用途 | 类比 |
|-----|------|------|
| MCP | 连接工具 | USB接口，连接外设 |
| A2A | 连接Agent | 网络协议，设备通信 |

---

## 第五部分：与Claude协作开发指南

### 5.1 开发工作流

```
需求/问题
    │
    ▼
┌────────────────────────────────────────┐
│  第1步：描述需求                        │
│  - 我想实现什么功能？                    │
│  - 当前遇到什么问题？                    │
│  - 期望的结果是什么？                    │
└────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────┐
│  第2步：Claude分析                      │
│  - 理解需求                             │
│  - 探索代码库                           │
│  - 设计方案                             │
└────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────┐
│  第3步：确认方案                        │
│  - 查看Claude的设计                     │
│  - 提出修改意见                         │
│  - 确认后再实现                         │
└────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────┐
│  第4步：Claude实现                      │
│  - 编写代码                             │
│  - 运行测试                             │
│  - 修复问题                             │
└────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────┐
│  第5步：验证验收                        │
│  - 功能是否符合预期？                    │
│  - 代码质量是否满意？                    │
│  - 是否需要调整？                        │
└────────────────────────────────────────┘
```

### 5.2 高效提问模板

**场景1：实现新功能**
```
我想实现 [具体功能]，用于 [使用场景]。

相关上下文：
- 这个功能属于 [模块名] 模块
- 需要与 [已有功能] 联动
- 参考 [类似实现] 的实现方式

期望的输入输出：
- 输入：[示例]
- 输出：[示例]
```

**场景2：修复Bug**
```
我遇到了一个问题：[问题描述]

错误信息：
```
[错误日志]
```

复现步骤：
1. [步骤1]
2. [步骤2]
3. [步骤3]

期望行为：[应该发生什么]
实际行为：[实际发生什么]
```

**场景3：理解代码**
```
请帮我理解这段代码：
- 文件：[文件路径]
- 函数：[函数名]

我不理解的部分：
- [具体问题1]
- [具体问题2]
```

**场景4：代码审查**
```
请帮我审查 [文件/模块] 的代码，关注：
- 代码质量
- 潜在bug
- 性能问题
- 安全漏洞
```

### 5.3 常用命令速查

| 需求 | 如何问Claude |
|-----|-------------|
| 查看项目结构 | "请帮我探索这个项目的架构" |
| 查找某个功能 | "我想找 [功能名] 在哪里实现的" |
| 添加API接口 | "我想添加一个 [描述] 的API接口" |
| 修改数据库 | "需要添加 [字段/表]，怎么操作？" |
| 调试问题 | "遇到了 [错误]，帮我分析一下" |
| 前端联调 | "前端调用 [API] 报错了，看看后端" |
| 性能优化 | "这个接口很慢，怎么优化？" |
| 添加测试 | "给 [模块] 添加单元测试" |

---

## 第六部分：AI Agent面试知识点

### 6.1 核心概念

**1. 什么是Agent？**

Agent = LLM + 规划能力 + 记忆 + 工具使用

```
传统LLM调用：
用户 ──> LLM ──> 回复

Agent模式：
用户 ──> Agent ──> 思考/规划 ──> 选择工具 ──> 执行 ──> 观察 ──> 回复
                      ^                                        │
                      └────────────────────────────────────────┘
```

**2. ReAct模式 (Reasoning + Acting)**

```
Thought: 我需要搜索最新的天气信息
Action: search_tool(query="北京今天天气")
Observation: 北京今天晴，25°C
Thought: 现在可以回答用户了
Final Answer: 北京今天天气晴朗，气温25度
```

**3. 记忆系统**

| 记忆类型 | 存储内容 | 示例 |
|---------|---------|------|
| 短期记忆 | 当前对话历史 | 本轮对话的messages |
| 长期记忆 | 用户偏好、知识 | 用户喜欢Python |
| 向量记忆 | 语义相似检索 | 相关文档片段 |

### 6.2 架构设计题

**Q1：如何设计一个支持多轮对话的AI Agent系统？**

**答题要点：**
```
1. 会话管理 (Session)
   - 会话ID唯一标识
   - 维护对话历史
   - 支持会话状态（运行中/已完成）

2. 消息存储 (Message)
   - 角色：system/user/assistant/tool
   - 内容：文本/图片/文件
   - 时间戳、token数

3. 上下文窗口管理
   - 滑动窗口：保留最近N条
   - 摘要压缩：历史消息生成摘要
   - 向量检索：检索相关历史

4. 并发控制
   - 同一会话串行处理
   - 不同会话并行处理
```

**Q2：如何设计Agent的工具调用系统？**

**答题要点：**
```
1. 工具定义 (Tool Definition)
   - name: 工具名称
   - description: 功能描述
   - parameters: JSON Schema

2. 工具注册 (Tool Registry)
   - 动态加载工具配置
   - 支持MCP/A2A协议

3. 调用流程
   LLM输出工具调用意图
        ↓
   解析tool_calls
        ↓
   参数校验
        ↓
   执行工具
        ↓
   返回观察结果
        ↓
   LLM生成最终回复

4. 错误处理
   - 工具不存在
   - 参数错误
   - 执行超时
   - 结果解析失败
```

### 6.3 技术实现题

**Q3：如何实现LLM流式输出？**

**代码要点：**
```python
async def stream_chat(messages: list) -> AsyncGenerator[str, None]:
    """流式生成回复"""
    response = await openai.chat.completions.create(
        model="gpt-4",
        messages=messages,
        stream=True  # 启用流式
    )
    
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# SSE返回给前端
@app.post("/chat")
async def chat(request: ChatRequest):
    async def event_generator():
        async for text in stream_chat(request.messages):
            yield {"data": json.dumps({"content": text})}
    
    return EventSourceResponse(event_generator())
```

**Q4：如何实现安全的代码执行环境？**

**答题要点：**
```
1. 沙箱隔离 (Sandbox)
   - Docker容器隔离
   - 资源限制（CPU/内存/时间）
   - 网络隔离/受限访问

2. 代码审计
   - 危险函数检测
   - 导入白名单
   - 语法检查

3. 执行监控
   - 超时控制
   - 资源监控
   - 日志记录

4. 文件系统隔离
   - 临时工作目录
   - 只读挂载
   - 执行后清理
```

### 6.4 性能优化题

**Q5：AI Agent系统有哪些性能优化点？**

| 层面 | 优化策略 |
|-----|---------|
| LLM调用 | 1. 缓存常见查询<br>2. 模型分级（简单任务用小模型）<br>3. 异步批量处理 |
| 上下文 | 1. 历史消息截断<br>2. 向量化检索<br>3. 智能摘要 |
| 工具调用 | 1. 并行执行独立工具<br>2. 缓存工具结果<br>3. 超时控制 |
| 架构层面 | 1. 连接池<br>2. 消息队列削峰<br>3. 水平扩展 |

### 6.5 安全设计题

**Q6：AI Agent系统需要考虑哪些安全问题？**

```
1. Prompt注入防护
   - 输入过滤/转义
   - 系统提示加固
   - 输出校验

2. 工具调用安全
   - 权限控制
   - 危险操作确认
   - 执行审计

3. 数据安全
   - 敏感信息脱敏
   - 数据加密存储
   - 访问控制

4. 资源安全
   - 限流防刷
   - 成本上限
   - 异常检测
```

---

## 第七部分：实操示例

### 7.1 添加一个新的API接口

**需求：** 添加一个获取会话统计信息的接口

**步骤1：定义路由**
```python
# api/app/interfaces/endpoints/session_routes.py

@router.get(
    path="/{session_id}/stats",
    response_model=Response[SessionStatsResponse],
    summary="获取会话统计信息",
)
async def get_session_stats(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
) -> Response[SessionStatsResponse]:
    """获取指定会话的消息数、token消耗等统计信息"""
    stats = await session_service.get_session_stats(session_id)
    return Response.success(data=stats)
```

**步骤2：定义Schema**
```python
# api/app/interfaces/schemas/session.py

class SessionStatsResponse(BaseModel):
    message_count: int      # 消息总数
    user_messages: int      # 用户消息数
    ai_messages: int        # AI消息数
    total_tokens: int       # 总token消耗
    avg_response_time: float  # 平均响应时间
```

**步骤3：实现服务层**
```python
# api/app/application/services/session_service.py

async def get_session_stats(self, session_id: str) -> SessionStatsResponse:
    session = await self.get_session(session_id)
    
    events = session.events
    user_count = sum(1 for e in events if e.role == "user")
    ai_count = sum(1 for e in events if e.role == "assistant")
    
    total_tokens = sum(
        e.token_count for e in events 
        if e.token_count
    )
    
    return SessionStatsResponse(
        message_count=len(events),
        user_messages=user_count,
        ai_messages=ai_count,
        total_tokens=total_tokens,
        avg_response_time=0.0  # 可扩展计算
    )
```

**步骤4：前端调用**
```typescript
// ui/src/lib/api/session.ts

getSessionStats: (sessionId: string): Promise<SessionStats> => {
  return get<SessionStats>(`/sessions/${sessionId}/stats`);
},
```

### 7.2 添加一个新的MCP工具

**配置示例：**
```yaml
mcp_config:
  mcpServers:
    my-custom-tool:
      transport: streamable_http
      enabled: true
      url: https://my-tool.com/mcp
      headers:
        Authorization: Bearer ${TOOL_API_KEY}
```

**使用方式：**
Agent会自动从配置加载MCP服务，无需修改代码。

---

## 附录：术语表

| 术语 | 解释 |
|-----|------|
| API | 应用程序接口，软件间通信的契约 |
| REST | 一种API设计风格，使用HTTP方法 |
| JSON | 数据交换格式，键值对结构 |
| SSE | 服务端推送事件，单向实时通信 |
| WebSocket | 全双工通信协议 |
| ORM | 对象关系映射，操作数据库的抽象层 |
| DDD | 领域驱动设计，软件设计方法论 |
| DI | 依赖注入，解耦组件的技术 |
| MCP | Model Context Protocol，AI工具连接协议 |
| A2A | Agent-to-Agent，Agent间通信协议 |
| LLM | 大语言模型，如GPT、Claude |
| Token | 模型处理文本的基本单位 |
| Prompt | 给模型的输入指令 |
| RAG | 检索增强生成，结合向量检索的生成 |

---

**文档版本：** 1.0  
**适用项目：** GoodManus AI Agent 系统  
**编写目标：** 算法工程师转型AI Agent开发
