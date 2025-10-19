# ResearchMind 环境变量详细指南

## 1. 环境变量分类

### 1.1 服务监听配置（*_MCP_HOST 和 *_MCP_PORT）

这些变量控制MCP服务**监听**的地址和端口。

```
*_MCP_HOST：MCP服务监听的地址
*_MCP_PORT：MCP服务监听的端口
```

**为什么MCP服务只监听127.0.0.1？**

- MCP服务是内部服务，仅被后端HTTP API调用
- 不需要暴露到外网
- 限制仅本地访问，提高安全性

**示例**：
```bash
DATABASE_MCP_HOST=127.0.0.1    # 数据库MCP监听127.0.0.1
DATABASE_MCP_PORT=50002         # 监听端口50002
```

### 1.2 客户端连接配置（*_MCP_URL）

这些变量控制后端HTTP API**连接**MCP服务时使用的地址。

```
*_MCP_URL：后端HTTP API连接MCP服务的完整URL
```

**为什么需要这个变量？**

1. **分布式部署支持**
   - 在Docker/Kubernetes环境中，MCP服务可能运行在不同的容器/Pod中
   - 后端API需要通过网络连接到MCP服务
   - 本地监听地址（127.0.0.1）和远程连接地址（域名）不同

2. **灵活的部署方式**
   - 单机部署：MCP和后端API在同一台机器上
   - 分布式部署：MCP和后端API在不同机器上
   - 容器化部署：使用容器网络通信

**示例**：

**本地部署**：
```bash
# MCP服务监听
DATABASE_MCP_HOST=127.0.0.1
DATABASE_MCP_PORT=50002

# 后端API连接（本地）
DATABASE_MCP_URL=http://127.0.0.1:50002/sse
```

**远程部署**：
```bash
# MCP服务监听（仍然是本地）
DATABASE_MCP_HOST=127.0.0.1
DATABASE_MCP_PORT=50002

# 后端API连接（通过域名）
DATABASE_MCP_URL=http://dyum1393797.bohrium.tech:50002/sse
```

---

## 2. 为什么不需要0.0.0.0？

### 2.1 0.0.0.0的含义

```
0.0.0.0 = 监听所有网络接口
```

当服务监听0.0.0.0时，它会接受来自任何网络接口的连接。

### 2.2 MCP服务为什么不需要0.0.0.0？

**原因1：内部通信**
- MCP服务只被后端HTTP API调用
- 后端API和MCP服务在同一台机器上
- 使用127.0.0.1（localhost）就足够了

**原因2：安全性**
- 如果MCP监听0.0.0.0，任何人都可以直接访问MCP服务
- 绕过后端API的权限验证
- 可能导致数据泄露或被滥用

**原因3：资源保护**
- MCP服务执行计算密集型任务
- 如果暴露外网，可能被恶意用户滥用
- 后端API可以实现速率限制、请求队列等保护机制

### 2.3 通过域名访问时的流程

```
用户浏览器
  ↓
http://dyum1393797.bohrium.tech:50001（前端UI）
  ↓
前端发送请求到后端API
  ↓
http://dyum1393797.bohrium.tech:50006（后端HTTP API）
  ↓
后端API连接MCP服务
  ↓
http://127.0.0.1:50002/sse（MCP服务，仅本地）
  ↓
MCP返回结果给后端API
  ↓
后端API返回结果给前端
  ↓
前端显示结果
```

**关键点**：
- 前端通过域名访问前端UI和后端API
- 后端API通过127.0.0.1访问MCP服务
- MCP服务不需要暴露到外网

---

## 3. 前端UI为什么需要0.0.0.0？

前端UI需要监听0.0.0.0是因为：

1. **外部访问**
   - 前端UI需要被浏览器访问
   - 浏览器可能来自不同的机器
   - 需要监听所有网络接口

2. **配置示例**
   ```bash
   VITE_FRONTEND_HOST=0.0.0.0
   VITE_FRONTEND_PORT=50001
   ```

3. **访问方式**
   - 本地：http://127.0.0.1:50001
   - 远程：http://dyum1393797.bohrium.tech:50001

---

## 4. 环境变量总结

### 4.1 前端UI
```bash
VITE_FRONTEND_HOST=0.0.0.0          # 监听所有接口
VITE_FRONTEND_PORT=50001             # 前端端口
```

### 4.2 后端HTTP API
```bash
RESEARCHMIND_HTTP_HOST=127.0.0.1    # 仅本地监听
RESEARCHMIND_HTTP_PORT=50002         # 后端API端口
RESEARCHMIND_API_URL=http://dyum1393797.bohrium.tech:50002  # 前端调用地址
```

### 4.3 WebSocket
```bash
RESEARCHMIND_WS_HOST=127.0.0.1      # 仅本地监听
RESEARCHMIND_WS_PORT=50003           # WebSocket端口
VITE_WS_URL=ws://dyum1393797.bohrium.tech:50003/ws  # 前端连接地址
```

### 4.4 MCP服务（以Database为例）
```bash
# 服务监听配置
DATABASE_MCP_HOST=127.0.0.1          # 仅本地监听
DATABASE_MCP_PORT=50006               # 服务端口

# 客户端连接配置
DATABASE_MCP_URL=http://dyum1393797.bohrium.tech:50006/sse  # 后端API连接地址
```

---

## 5. 配置规则

### 规则1：监听地址
- **前端UI**：0.0.0.0（允许外部访问）
- **后端API**：127.0.0.1（仅本地）
- **MCP服务**：127.0.0.1（仅本地）
- **WebSocket**：127.0.0.1（仅本地）

### 规则2：连接地址
- **前端调用后端API**：使用VITE_API_URL（域名）
- **前端连接WebSocket**：使用VITE_WS_URL（域名）
- **后端API调用MCP**：使用*_MCP_URL（域名）

### 规则3：本地开发
- 所有连接地址使用127.0.0.1
- 示例：http://127.0.0.1:50006

### 规则4：远程部署
- 所有连接地址使用域名
- 示例：http://dyum1393797.bohrium.tech:50006

---

## 6. 常见问题

### Q: 为什么只需要DATABASE_MCP_URL而不需要DATABASE_HOST？

A:
- `DATABASE_MCP_URL`：包含完整的URL和路径，支持分布式部署
- 不需要单独的`DATABASE_HOST`变量，因为URL已经包含了所有必要的信息
- 这样配置更简洁，避免重复定义

### Q: 如何在Docker中部署？

A:
```bash
# Docker容器内
DATABASE_MCP_HOST=0.0.0.0            # 监听所有接口（容器内）
DATABASE_MCP_PORT=50002

# 后端API连接
DATABASE_MCP_URL=http://database-mcp:50002/sse  # 使用容器名称
```

### Q: 如何在Kubernetes中部署？

A:
```bash
# Kubernetes Pod内
DATABASE_MCP_HOST=0.0.0.0            # 监听所有接口（Pod内）
DATABASE_MCP_PORT=50002

# 后端API连接
DATABASE_MCP_URL=http://database-mcp-service:50002/sse  # 使用Service名称
```

---

## 7. 最佳实践

1. **本地开发**
   - 使用.env或.env.local
   - 所有地址使用127.0.0.1

2. **远程部署**
   - 使用.env.bohr
   - 所有连接地址使用域名
   - 监听地址保持127.0.0.1（除了前端UI）

3. **容器化部署**
   - MCP服务监听0.0.0.0（容器内）
   - 使用容器名称或Service名称作为连接地址

4. **安全性**
   - 后端API和MCP服务不暴露到外网
   - 所有外部请求通过前端UI和后端API
   - 后端API负责权限验证

---

## 8. 自动域名检测方案（推荐）

### 8.1 概述

当不知道具体的部署域名时，可以使用自动域名检测方案。前端会自动检测当前访问的域名，无需在环境变量中指定具体的域名。

### 8.2 环境变量配置

```bash
# 后端监听配置 - 监听所有接口
RESEARCHMIND_HTTP_HOST=0.0.0.0
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=0.0.0.0
RESEARCHMIND_WS_PORT=50003

# 前端连接配置 - 使用相对路径（自动检测）
VITE_API_URL=/api
VITE_WS_URL=/ws
```

### 8.2.1 配置文件（.env.bohr）

```bash
# ==========================================
# Service Listening Configuration
# ==========================================
# 推荐部署方案：使用 Nginx 反向代理 + 自动域名检测

# 后端监听所有接口
RESEARCHMIND_HTTP_HOST=0.0.0.0
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=0.0.0.0
RESEARCHMIND_WS_PORT=50003

# ==========================================
# Client Connection Configuration (Auto-detect domain)
# ==========================================
# 前端连接配置 - 自动检测域名（通过 Nginx 反向代理）

# API连接地址 - 使用相对路径 /api（自动检测域名）
VITE_API_URL=/api

# WebSocket连接地址 - 使用相对路径 /ws（自动检测域名）
VITE_WS_URL=/ws
```

### 8.3 工作原理

#### 前端自动检测流程

```
1. 用户访问 http://example.com
   ↓
2. 前端检测当前域名：example.com
   ↓
3. 前端检测当前协议：http 或 https
   ↓
4. 前端构建完整 URL：http://example.com:50002/api
   ↓
5. 前端调用后端 API
```

#### 代码实现

```typescript
// ui/src/constants/index.ts
const resolveRuntimeLocation = () => {
  const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
  const hostname = window.location.hostname || '127.0.0.1'
  return {
    protocol,
    hostname,
    isHttps: protocol === 'https:',
  }
}

// 如果 VITE_API_URL 是相对路径，自动转换为完整 URL
const resolveApiUrl = (envUrl?: string): string => {
  if (!envUrl) {
    return buildDefaultApiUrl()
  }

  // 如果是相对路径（以 / 开头），转换为完整 URL
  if (envUrl.startsWith('/')) {
    const { protocol, hostname } = resolveRuntimeLocation()
    const port = import.meta.env.VITE_API_PORT || '50002'
    return `${protocol}//${hostname}:${port}${envUrl}`
  }

  // 如果是完整 URL，直接返回
  return envUrl
}
```

### 8.4 部署场景

#### 场景1：本地开发

```bash
# 访问：http://localhost:50001
# 前端自动检测：localhost
# 构建 API URL：http://localhost:50002/api
```

#### 场景2：远程服务器（无反向代理）

```bash
# 访问：http://your-domain.com:50001
# 前端自动检测：your-domain.com
# 构建 API URL：http://your-domain.com:50002/api
```

#### 场景3：反向代理部署（推荐）

```bash
# Nginx 配置
server {
    listen 80;
    server_name _;  # 接受任意域名

    location / {
        proxy_pass http://localhost:50001;
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://localhost:50002/api/;
        proxy_set_header Host $host;
    }

    location /ws {
        proxy_pass http://localhost:50003/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# 访问：http://example.com
# 前端自动检测：example.com
# 构建 API URL：http://example.com/api
```

### 8.5 优点

1. **无需配置域名** - 自动检测当前访问的域名
2. **支持任意域名** - 无需修改配置即可部署到不同域名
3. **支持 HTTPS** - 自动检测协议（HTTP/HTTPS）
4. **简化部署** - 一套配置适用所有场景
5. **灵活迁移** - 轻松迁移到新域名无需修改代码

### 8.6 一键部署

```bash
# 克隆项目
git clone <repository-url>
cd ResearchMind

# 赋予执行权限
chmod +x start.sh

# 一键启动（自动配置所有环境）
./start.sh

# 访问应用
# 本地：http://localhost:50001
# 远程：http://your-domain.com（需要配置 Nginx 反向代理）
```

