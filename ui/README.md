# GoodManus 前端 UI

基于 Next.js 构建的前端用户界面，提供会话管理、AI 对话、远程桌面（VNC）等交互功能。

## 技术栈

- Next.js 16 (React 19)
- TypeScript
- Tailwind CSS 4
- Radix UI (组件库)
- noVNC (远程桌面)

## 项目结构

```
ui/
├── src/
│   ├── app/               # 页面路由
│   │   ├── page.tsx       # 首页
│   │   ├── sessions/      # 会话页面
│   │   └── layout.tsx     # 根布局
│   ├── components/        # 组件
│   │   ├── ui/            # 基础 UI 组件（shadcn/ui）
│   │   ├── tool-use/      # 工具使用相关组件
│   │   ├── vnc-overlay.tsx    # VNC 远程桌面覆盖层
│   │   └── vnc-viewer.tsx     # VNC 查看器组件
│   ├── lib/
│   │   └── api/           # API 客户端
│   │       ├── fetch.ts   # 核心 fetch 封装
│   │       ├── config.ts  # 配置 API
│   │       ├── session.ts # 会话 API
│   │       ├── file.ts    # 文件 API
│   │       └── types.ts   # 类型定义
│   ├── hooks/             # 自定义 Hooks
│   └── providers/         # Context Providers
├── public/                # 静态资源
├── next.config.ts         # Next.js 配置
├── .env.local             # 本地环境变量
├── .env.production        # 生产环境变量
├── Dockerfile
├── package.json
└── tsconfig.json
```

## API 调用配置

项目通过环境变量 `NEXT_PUBLIC_API_BASE_URL` 配置 API 地址：

### 开发环境

`.env.local`：
```bash
# 开发环境直连 API 服务
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

### 生产环境

`.env.production` 或 Dockerfile 构建参数：
```bash
# 生产环境使用相对路径，由 Nginx 代理
NEXT_PUBLIC_API_BASE_URL=/api
```

### 运行时构建

Dockerfile 中通过构建参数注入：

```dockerfile
ARG NEXT_PUBLIC_API_BASE_URL=/api
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
```

## 本地开发

### 环境准备

- Node.js >= 22
- npm >= 10

### 安装与启动

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

开发服务器运行在 `http://localhost:3000`，API 请求转发到 `http://localhost:8000/api`。

### 开发环境配置

1. 确保 `.env.local` 配置正确：
   ```bash
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
   ```

2. 确保后端 API 服务已启动：
   ```bash
   cd ../api
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 构建

```bash
# 开发构建
npm run build

# 生产构建（使用生产环境变量）
NODE_ENV=production npm run build

# 启动生产服务器
npm run start
```

## Docker 部署

UI 服务通过根目录的 `docker-compose.yml` 统一部署。

### Dockerfile 多阶段构建

1. **deps** - 安装 npm 依赖
2. **builder** - 构建 Next.js 应用（standalone 模式）
3. **runner** - 最小化生产镜像

### 构建参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `NEXT_PUBLIC_API_BASE_URL` | API 基础地址 | `/api` |

### 构建命令

```bash
# 本地构建测试
docker build --build-arg NEXT_PUBLIC_API_BASE_URL=/api -t manus-ui .

# 运行测试
docker run -p 3000:3000 manus-ui
```

## Next.js 配置

`next.config.ts`：

```typescript
const nextConfig = {
  output: "standalone",  // 生成独立部署包
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.myqcloud.com",  // 腾讯云 COS 图片域名
      },
    ],
    formats: ["image/webp", "image/avif"],
    minimumCacheTTL: 60,
  },
  experimental: {
    optimizeCss: true,
  },
};
```

## VNC 远程桌面

VNC 功能通过 noVNC 库实现，API 服务提供 WebSocket 代理。

### VNC URL 构建

```typescript
function buildVNCUrl(sessionId: string): string {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
  
  // 解析 API 地址构建 WebSocket URL
  const url = new URL(apiBase);
  const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  
  return `${protocol}//${url.host}${url.pathname}/sessions/${sessionId}/vnc`;
}
```

### 使用方式

1. 在会话页面点击"远程桌面"按钮
2. 组件通过 `buildVNCUrl` 构建 WebSocket URL
3. noVNC 组件连接到 API 的 WebSocket 端点
4. API 代理连接到沙箱的 VNC 服务

## 图片处理

项目使用腾讯云 COS 存储图片，Next.js Image 组件优化加载：

```typescript
// next.config.ts
images: {
  remotePatterns: [
    {
      protocol: "https",
      hostname: "**.myqcloud.com",
    },
  ],
}
```

使用方式：

```tsx
import Image from "next/image";

<Image
  src="https://your-bucket.cos.ap-chongqing.myqcloud.com/image.png"
  alt="描述"
  width={800}
  height={600}
/>
```

## API 客户端

统一的 API 客户端封装在 `src/lib/api/fetch.ts`：

```typescript
// GET 请求
const data = await get("/sessions");

// POST 请求
const result = await post("/sessions", { title: "新会话" });

// SSE 流式请求
const stream = await createSSEStream("/sessions/123/chat", { message: "你好" });
```

## 故障排查

### 图片无法加载

检查 `next.config.ts` 中的图片域名配置是否包含 COS 域名。

### API 请求失败

1. 检查 `.env.local` 中的 `NEXT_PUBLIC_API_BASE_URL` 配置
2. 确保 API 服务已启动
3. 检查浏览器开发者工具的网络面板

### 构建失败

```bash
# 清除缓存
rm -rf .next
rm -rf node_modules
npm install
npm run build
```

### VNC 连接失败

1. 确保会话有活跃的沙箱环境
2. 检查 API 服务的 WebSocket 连接
3. 查看浏览器控制台错误信息
