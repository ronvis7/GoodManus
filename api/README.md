# GoodManus API 服务

基于 FastAPI 构建的后端 API 服务，提供会话管理、AI Agent 调度、文件处理、沙箱管理等核心功能。

## 技术栈

- Python 3.12+
- FastAPI + Uvicorn
- SQLAlchemy (asyncpg) + Alembic
- Redis (异步客户端)
- Docker SDK (沙箱管理)
- Playwright (浏览器自动化)
- WebSocket (VNC 代理转发)

## 项目结构

```
api/
├── app/
│   ├── application/       # 应用层（业务服务编排）
│   ├── domain/            # 领域层（核心业务逻辑）
│   ├── infrastructure/    # 基础设施层（外部服务集成）
│   │   ├── external/      # 沙箱、浏览器等外部服务
│   │   ├── storage/       # PostgreSQL、Redis、COS 存储
│   │   └── models/        # ORM 模型
│   ├── interfaces/        # 接口层（API 端点）
│   │   ├── endpoints/     # 路由定义
│   │   └── schemas/       # 请求/响应模型
│   └── main.py            # 应用入口
├── alembic/               # 数据库迁移
├── core/
│   └── config.py          # 配置管理（Pydantic Settings）
├── .env                   # 环境变量
├── alembic.ini            # Alembic 配置文件
├── config.yaml            # 应用配置（LLM、MCP、A2A）
├── Dockerfile
├── requirements.txt
└── run.sh                 # 启动脚本
```

## API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 健康检查 |
| GET/POST | `/api/app-config/*` | 应用配置管理 |
| POST | `/api/files` | 文件上传 |
| GET | `/api/files/{id}/download` | 文件下载 |
| POST | `/api/sessions` | 创建会话 |
| POST | `/api/sessions/stream` | SSE 流式获取会话列表 |
| GET | `/api/sessions` | 获取会话列表 |
| GET | `/api/sessions/{id}` | 获取会话详情 |
| POST | `/api/sessions/{id}/chat` | SSE 流式对话 |
| POST | `/api/sessions/{id}/stop` | 停止会话 |
| POST | `/api/sessions/{id}/delete` | 删除会话 |
| GET | `/api/sessions/{id}/files` | 获取会话文件列表 |
| POST | `/api/sessions/{id}/file` | 读取会话文件内容 |
| POST | `/api/sessions/{id}/shell` | 读取 Shell 输出 |
| WS | `/api/sessions/{id}/vnc` | VNC WebSocket 代理 |

## 本地开发

### 环境准备

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 3. 安装依赖
pip install uv
uv pip install -r requirements.txt

# 4. 安装 Playwright 浏览器
playwright install
```

### 配置环境变量

修改 `.env` 文件，将数据库和 Redis 地址改为 `localhost`：

```bash
# 开发环境使用 localhost
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://postgres:postgres@localhost:5432/manus
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# 沙箱配置（留空则动态创建沙箱容器）
SANDBOX_ADDRESS=
SANDBOX_IMAGE=sandbox-dev

# Docker 配置（Windows/Mac 使用 TCP）
DOCKER_HOST=tcp://localhost:2375
# Linux 使用 Unix socket
# DOCKER_HOST=unix:///var/run/docker.sock

# 腾讯云 COS 配置
COS_SECRET_ID=your_secret_id
COS_SECRET_KEY=your_secret_key
COS_REGION=ap-chongqing
COS_BUCKET=your_bucket_name
```

### 配置 Alembic

开发环境中，修改 `alembic.ini` 中的数据库连接：

```ini
sqlalchemy.url = postgresql+psycopg2://postgres:postgres@localhost:5432/manus
```

### 启动依赖服务

```bash
# 使用 Docker Compose 启动数据库和 Redis
docker compose -f ../docker-compose.yml up -d manus-postgres manus-redis
```

### 启动服务

```bash
# 方式1：使用启动脚本
./run.sh

# 方式2：直接使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问 `http://localhost:8000/docs` 查看 API 文档。

### 数据库迁移

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1

# 查看当前版本
alembic current

# 查看历史版本
alembic history --verbose
```

## Docker 部署

API 服务通过根目录的 `docker-compose.yml` 统一部署。

### 构建镜像

```bash
docker build -t manus-api .
```

### 环境变量

Docker 部署时，环境变量由根目录 `.env` 文件和 `docker-compose.yml` 提供：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ENV` | 运行环境 | production |
| `LOG_LEVEL` | 日志级别 | INFO |
| `SQLALCHEMY_DATABASE_URI` | 数据库连接 | postgresql+asyncpg://postgres:postgres@manus-postgres:5432/manus |
| `REDIS_HOST` | Redis 主机 | manus-redis |
| `REDIS_PORT` | Redis 端口 | 6379 |
| `DOCKER_HOST` | Docker 连接地址 | unix:///var/run/docker.sock |
| `SANDBOX_ADDRESS` | 沙箱地址（留空动态创建） | manus-sandbox |
| `COS_SECRET_ID` | 腾讯云 COS SecretId | 从 .env 读取 |
| `COS_SECRET_KEY` | 腾讯云 COS SecretKey | 从 .env 读取 |
| `COS_BUCKET` | COS 存储桶名称 | 从 .env 读取 |

## WebSocket VNC 代理

API 服务提供 WebSocket 端点 `/api/sessions/{session_id}/vnc`，用于代理前端与沙箱 VNC 的连接：

1. 前端通过 WebSocket 连接到 API 的 VNC 端点
2. API 根据 session_id 获取对应沙箱的 VNC WebSocket URL
3. API 建立与沙箱的双向 WebSocket 连接
4. 数据在前端和沙箱之间双向转发

### 实现细节

- 使用 `fastapi.WebSocket` 接收前端连接
- 使用 `websockets` 库连接沙箱
- 使用 `asyncio` 创建双向数据转发任务
- 支持 binary 和 base64 子协议

## 故障排查

### 数据库连接失败

```bash
# 检查数据库服务状态
docker compose exec manus-postgres pg_isready -U postgres

# 检查网络连接
docker compose exec manus-api nc -zv manus-postgres 5432
```

### 沙箱连接失败

```bash
# 检查沙箱状态
docker compose exec manus-api curl http://manus-sandbox:8080/api/supervisor/status

# 检查沙箱网络
docker network inspect manus-network
```

### 权限问题

确保 Docker socket 挂载正确：

```bash
# 检查 Docker socket
ls -la /var/run/docker.sock

# 在 Windows/Mac 上确保 Docker Desktop 设置正确
```
