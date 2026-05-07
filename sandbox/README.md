# GoodManus 沙箱服务

基于 Ubuntu 22.04 构建的沙箱环境，提供隔离的代码执行、浏览器自动化和远程桌面访问能力。

## 技术栈

- Ubuntu 22.04
- Python 3.10 + FastAPI
- Node.js 24 (LTS)
- Chromium (浏览器自动化)
- Xvfb + x11vnc + websockify (虚拟显示 + VNC)
- Supervisor (进程管理)

## 架构

沙箱通过 Supervisor 管理多个进程：

| 进程 | 端口 | 说明 |
|------|------|------|
| FastAPI | 8080 | REST API（文件操作、Shell 执行） |
| Chrome | 8222 (内部) | 浏览器实例 |
| socat | 9222 | Chrome DevTools Protocol 代理 |
| Xvfb | - | 虚拟显示器 (:1) |
| x11vnc | 5900 | VNC 服务 |
| websockify | 5901 | WebSocket VNC 代理 |

## 项目结构

```
sandbox/
├── app/                   # FastAPI 应用
│   ├── api/               # API 路由
│   │   ├── file/          # 文件操作接口
│   │   ├── shell/         # Shell 执行接口
│   │   └── supervisor/    # 进程状态接口
│   └── main.py            # 应用入口
├── supervisord.conf       # Supervisor 配置
├── Dockerfile
├── requirements.txt
└── README.md
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/file/read-file` | 读取文件内容 |
| POST | `/api/file/write-file` | 写入文件内容 |
| POST | `/api/file/replace-in-file` | 替换文件内容 |
| POST | `/api/file/search-in-file` | 搜索文件内容 |
| POST | `/api/file/find-files` | 查找文件 |
| POST | `/api/file/upload-file` | 上传文件 |
| GET | `/api/file/download-file` | 下载文件 |
| POST | `/api/shell/exec-command` | 执行 Shell 命令 |
| POST | `/api/shell/read-shell-output` | 读取 Shell 输出 |
| POST | `/api/shell/write-shell-input` | 写入 Shell 输入 |
| POST | `/api/shell/wait-process` | 等待进程结束 |
| POST | `/api/shell/kill-process` | 终止进程 |
| GET | `/api/supervisor/status` | 获取进程状态 |

## 本地开发

### 使用开发容器

```bash
cd .devops
docker compose up -d

# SSH 连接到开发容器
ssh root@localhost -p 2222
# 密码: root
```

### 启动服务

在容器内或本地：

```bash
# 安装依赖
pip3 install -r requirements.txt

# 启动 API 服务
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 启动所有进程（Supervisor）

```bash
supervisord -n -c supervisord.conf
```

## Docker 部署

沙箱服务通过根目录的 `docker-compose.yml` 统一部署。

### 构建镜像

```bash
docker build -t manus-sandbox .
```

### Dockerfile 说明

1. **基础镜像**: Ubuntu 22.04
2. **软件源**: 使用阿里云镜像源加速
3. **安装的软件**:
   - Python 3.10 + pip
   - Node.js 24 (LTS)
   - Chromium 浏览器
   - 中文字体（fonts-noto-cjk）
   - Xvfb、x11vnc、websockify
   - Supervisor

### 端口说明

在 Docker Compose 部署中，沙箱端口仅在容器网络内部可访问，不对外暴露：

- `8080` - FastAPI REST API
- `9222` - Chrome DevTools Protocol
- `5900` - VNC RFB（原始 VNC）
- `5901` - WebSocket VNC（通过 websockify 转发）

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SERVICE_TIMEOUT_MINUTES` | 服务超时时间（分钟） | 60 |
| `CHROME_ARGS` | Chrome 额外启动参数 | - |
| `HTTPS_PROXY` | HTTPS 代理地址 | - |
| `HTTP_PROXY` | HTTP 代理地址 | - |
| `NO_PROXY` | 不使用代理的地址 | - |

## Supervisor 配置

`supervisord.conf` 管理以下进程：

```ini
[group:services]
programs=xvfb,chrome,socat,x11vnc,websockify,app
```

### 启动顺序

1. **xvfb** (priority=10) - 虚拟显示器
2. **chrome** (priority=20) - Chrome 浏览器
3. **socat** (priority=30) - CDP 端口转发
4. **x11vnc** (priority=40) - VNC 服务
5. **websockify** (priority=50) - WebSocket VNC 代理
6. **app** (priority=60) - FastAPI 服务

### Chrome 配置

Chrome 以无沙箱模式启动，支持远程调试：

```bash
chromium \
    --display=:1 \
    --window-size=1280,1080 \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --remote-debugging-address=0.0.0.0 \
    --remote-debugging-port=8222
```

## VNC 连接

### 直接连接（容器内）

```bash
# VNC RFB 协议
vncviewer manus-sandbox:5900

# WebSocket 协议
# 使用 noVNC 连接到 ws://manus-sandbox:5901
```

### 通过 API 代理连接

API 服务提供 WebSocket 代理端点 `/api/sessions/{session_id}/vnc`，将前端连接转发到对应沙箱。

连接流程：

1. 前端通过 WebSocket 连接到 API 的 VNC 端点
2. API 根据 session_id 查找对应沙箱
3. API 建立与沙箱 websockify (5901) 的连接
4. 数据双向转发

## 故障排查

### 服务启动失败

查看 Supervisor 日志：

```bash
docker compose logs -f manus-sandbox
```

### Chrome 无法启动

检查资源限制：

```bash
# 检查内存
docker stats manus-sandbox

# 进入容器调试
docker compose exec manus-sandbox bash
supervisorctl status
supervisorctl tail chrome
```

### VNC 连接失败

```bash
# 检查 VNC 服务状态
docker compose exec manus-sandbox supervisorctl status x11vnc websockify

# 检查端口监听
docker compose exec manus-sandbox netstat -tlnp
```

### 中文显示问题

确保已安装中文字体：

```bash
docker compose exec manus-sandbox fc-list :lang=zh
```

## 安全注意事项

1. **沙箱隔离**: 每个任务会话运行在独立的沙箱容器中
2. **资源限制**: 生产环境建议设置 CPU/内存限制
3. **网络隔离**: 沙箱容器应限制对外网络访问
4. **数据清理**: 沙箱容器销毁时会自动清理数据
