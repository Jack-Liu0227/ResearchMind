# ResearchMind 部署指南

## 1. 部署方案对比

### 方案对比表

| 方案 | 配置方式 | 优点 | 缺点 | 适用场景 |
|------|--------|------|------|---------|
| 本地开发 | 指定 localhost | 简单直接 | 仅本地 | 开发调试 |
| 直接访问 | 指定具体域名 | 无需反向代理 | 需要知道域名 | 小规模部署 |
| 反向代理 | 相对路径 + 自动检测 | 灵活、自动检测 | 需要配置 Nginx | 生产环境（推荐） |

### 推荐方案：反向代理 + 自动域名检测

**优点**：
- 无需指定具体的域名
- 支持任意域名部署
- 自动检测 HTTP/HTTPS
- 一套配置适用所有场景

---

## 2. PaperSearch MCP 文件下载URL

### URL生成规则

PaperSearch MCP 生成的文件下载URL遵循以下规则：

```
{API_BASE_URL}/api/download/{file_path}
```

### 优先级

1. **优先使用 `VITE_API_URL`**（前端调用的API地址）
2. 如果未设置，则使用 `RESEARCHMIND_HTTP_HOST` + `RESEARCHMIND_HTTP_PORT`

### 示例

**本地开发环境（.env / .env.local）**：
```
VITE_API_URL=http://127.0.0.1:50002
```

生成的下载URL：
```
http://127.0.0.1:50002/api/download/papers/large_language_models_(llm)_bf434a7b/search_results_20251019_000938.csv
```

**反向代理部署环境（.env.bohr）**：
```
VITE_API_URL=/api
```

生成的下载URL（前端自动转换）：
```
http://your-domain.com/api/download/papers/large_language_models_(llm)_bf434a7b/search_results_20251019_000938.csv
```

### 支持的文件类型

- **CSV文件**：`csv_download_url`
  - 论文搜索结果
  - 分析结果
  - 报告论文列表

- **Markdown文件**：`md_download_url`
  - 论文总结报告
  - 分析报告

---

## 2. 远程虚拟机部署指南

### 2.1 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    远程虚拟机 (Bohrium)                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  前端UI (React)                                      │  │
│  │  监听: 0.0.0.0:50001                                │  │
│  │  访问: http://dyum1393797.bohrium.tech:50001        │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  后端HTTP API (FastAPI)                              │  │
│  │  监听: 127.0.0.1:50006（仅本地）                    │  │
│  │  访问: http://dyum1393797.bohrium.tech:50006        │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MCP Services (SSE)                                  │  │
│  │  - Paper Search: 127.0.0.1:50004                    │  │
│  │  - Simulation: 127.0.0.1:50005                      │  │
│  │  - Database: 127.0.0.1:50002                        │  │
│  │  - WebSocket: 127.0.0.1:50003                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 环境配置

#### 步骤1：使用.env.bohr配置

```bash
# 复制.env.bohr作为生产环境配置
cp .env.bohr .env.production

# 或直接使用.env.bohr
export ENV_FILE=.env.bohr
```

#### 步骤2：配置环境变量

编辑`.env.bohr`或`.env.production`，确保以下配置：

```bash
# ==========================================
# 服务监听配置
# ==========================================

# 前端UI - 监听所有接口（允许外部访问）
VITE_FRONTEND_HOST=0.0.0.0
VITE_FRONTEND_PORT=50001

# 后端API - 仅本地监听
RESEARCHMIND_HTTP_HOST=127.0.0.1
RESEARCHMIND_HTTP_PORT=50002

# WebSocket - 仅本地监听
RESEARCHMIND_WS_HOST=127.0.0.1
RESEARCHMIND_WS_PORT=50003

# MCP Services - 仅本地监听
PAPER_SEARCH_MCP_HOST=127.0.0.1
PAPER_SEARCH_MCP_PORT=50004
SIMULATION_MCP_HOST=127.0.0.1
SIMULATION_MCP_PORT=50005
DATABASE_MCP_HOST=127.0.0.1
DATABASE_MCP_PORT=50006

# ==========================================
# 客户端连接配置（使用域名）
# ==========================================

# 前端调用后端API的地址
VITE_API_URL=http://dyum1393797.bohrium.tech:50002

# WebSocket连接地址
VITE_WS_URL=ws://dyum1393797.bohrium.tech:50003/ws

# MCP服务连接地址
PAPER_SEARCH_MCP_URL=http://dyum1393797.bohrium.tech:50004/sse
SIMULATION_MCP_URL=http://dyum1393797.bohrium.tech:50005/sse
DATABASE_MCP_URL=http://dyum1393797.bohrium.tech:50006/sse
```

### 2.3 启动服务

#### 方式1：使用启动脚本

```bash
# 启动所有服务
python main.py --env .env.bohr
```

#### 方式2：分别启动各个服务

```bash
# 终端1：启动后端HTTP API
python -m services.http_server --env .env.bohr

# 终端2：启动Paper Search MCP
python mcp_servers/paper_search/server.py --env .env.bohr

# 终端3：启动Simulation MCP
python mcp_servers/simulation/server.py --env .env.bohr

# 终端4：启动Database MCP
python mcp_servers/database_call/server.py --env .env.bohr

# 终端5：启动前端UI
cd ui && npm run dev -- --host 0.0.0.0 --port 50001
```

### 2.4 访问应用

在浏览器中访问：

```
http://dyum1393797.bohrium.tech:50001
```

### 2.5 文件下载URL

部署后，文件下载URL将自动使用域名：

```
http://dyum1393797.bohrium.tech:50006/api/download/papers/{topic}/{filename}
```

---

## 3. 配置文件对比

| 配置项 | 本地开发 (.env) | 远程部署 (.env.bohr) |
|--------|-----------------|----------------------|
| 前端地址 | http://127.0.0.1:50001 | http://dyum1393797.bohrium.tech:50001 |
| API地址 | http://127.0.0.1:50006 | http://dyum1393797.bohrium.tech:50006 |
| WebSocket | ws://127.0.0.1:50003/ws | ws://dyum1393797.bohrium.tech:50003/ws |
| 服务监听 | 127.0.0.1 | 127.0.0.1 |

---

## 4. 常见问题

### Q: 为什么后端服务只监听127.0.0.1？

A: 出于安全考虑，后端服务只监听本地接口。前端通过域名访问时，实际上是访问虚拟机的公网IP，然后由虚拟机内部转发到127.0.0.1:50006。

### Q: 如何修改域名？

A: 编辑`.env.bohr`文件，将`dyum1393797.bohrium.tech`替换为你的实际域名：

```bash
# 替换所有出现的域名
sed -i 's/dyum1393797.bohrium.tech/your-domain.com/g' .env.bohr
```

### Q: 文件下载失败怎么办？

A: 检查以下几点：
1. 确保`VITE_API_URL`配置正确
2. 确保后端API服务正在运行
3. 检查文件是否存在于`./paper_search/`目录
4. 查看后端日志获取更多信息

---

## 5. 环境变量配置

### 配置文件说明

| 文件 | 用途 | 场景 |
|------|------|------|
| `.env` | 默认配置 | 本地开发 |
| `.env.local` | 本地覆盖 | 本地开发（优先级最高） |
| `.env.bohr` | 远程部署 | 生产环境（反向代理） |

### 推荐配置

#### 本地开发（.env）
```bash
VITE_API_URL=http://127.0.0.1:50002
VITE_WS_URL=ws://127.0.0.1:50003/ws
```

#### 远程部署（.env.bohr）- 推荐
```bash
# 后端监听所有接口
RESEARCHMIND_HTTP_HOST=0.0.0.0
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=0.0.0.0
RESEARCHMIND_WS_PORT=50003

# 前端使用相对路径（自动检测域名）
VITE_API_URL=/api
VITE_WS_URL=/ws
```

### URL生成优先级

1. **VITE_API_URL**（最高优先级）
   - 前端调用的API地址
   - 支持完整 URL 或相对路径
   - 相对路径会自动转换为完整 URL

2. **RESEARCHMIND_HTTP_HOST + RESEARCHMIND_HTTP_PORT**（备选）
   - 后端HTTP服务的监听地址
   - 仅在VITE_API_URL未设置时使用

### 代码实现

```python
# mcp_servers/paper_search/server.py
def get_api_base_url() -> str:
    """获取 API 基础 URL，支持多种配置方式"""
    api_url = os.getenv("VITE_API_URL")

    if api_url:
        # 支持相对路径和完整 URL
        return api_url

    # 备选方案：使用 RESEARCHMIND_HTTP_HOST + RESEARCHMIND_HTTP_PORT
    http_host = os.getenv("RESEARCHMIND_HTTP_HOST", "127.0.0.1")
    http_port = os.getenv("RESEARCHMIND_HTTP_PORT", "50002")

    # 如果监听地址是 0.0.0.0，使用 localhost 以支持反向代理
    if http_host == "0.0.0.0":
        http_host = "localhost"

    return f"http://{http_host}:{http_port}"
```

---

## 6. 反向代理部署（推荐）

### 使用 0.0.0.0 监听 + 反向代理

这种方式可以让应用部署在任意域名上，无需修改任何配置。

#### 环境变量配置

```bash
# 后端监听所有接口
RESEARCHMIND_HTTP_HOST=0.0.0.0
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=0.0.0.0
RESEARCHMIND_WS_PORT=50003

# 前端使用相对路径（自动检测）
VITE_API_URL=/api
VITE_WS_URL=/ws
```

#### Nginx 反向代理配置（自动匹配任意域名）

```nginx
# 自动匹配任意域名的反向代理配置
# 无需修改配置即可支持任意域名部署

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;  # 匹配所有域名

    # 前端 UI
    location / {
        proxy_pass http://localhost:50001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
    }

    # 后端 API - 使用相对路径
    location /api/ {
        proxy_pass http://localhost:50002/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
    }

    # WebSocket - 自动检测域名
    location /ws {
        proxy_pass http://localhost:50003/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_read_timeout 86400;
    }
}
```

#### 部署步骤

1. **复制 Nginx 配置**
```bash
# 创建配置文件
sudo tee /etc/nginx/sites-available/researchmind > /dev/null << 'EOF'
# 上面的 Nginx 配置内容
EOF

# 启用配置
sudo ln -s /etc/nginx/sites-available/researchmind /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

2. **访问应用**
```bash
# 本地访问
http://localhost:50001

# 远程访问（任意域名）
http://your-domain.com
http://another-domain.com
http://192.168.1.100
# 所有域名都会自动工作，无需修改配置
```

#### 优点

- ✅ **无需指定域名** - `server_name _;` 自动匹配所有域名
- ✅ **无需修改配置** - 支持任意域名部署
- ✅ **自动检测协议** - 前端自动检测 HTTP/HTTPS
- ✅ **一套配置** - 适用所有场景
- ✅ **灵活迁移** - 轻松迁移到新域名
- ✅ **安全性** - 后端服务不直接暴露，通过反向代理访问
- ✅ **可扩展性** - 可以轻松添加负载均衡、缓存等功能

---

## 7. 自动域名检测方案（推荐用于不知道域名的场景）

### 方案说明

当不知道具体的域名时，可以使用相对路径或自动检测的方式，让应用自动适配任意域名。

#### 环境变量配置

```bash
# 后端监听所有接口
RESEARCHMIND_HTTP_HOST=0.0.0.0
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=0.0.0.0
RESEARCHMIND_WS_PORT=50003

# 前端连接地址 - 使用相对路径（自动检测）
VITE_API_URL=/api
VITE_WS_URL=ws://localhost:50003/ws
```

#### 前端自动检测逻辑

前端会自动检测当前域名并构建完整的 URL：

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
const buildDefaultApiUrl = () => {
  const { protocol, hostname } = resolveRuntimeLocation()
  const port = import.meta.env.VITE_API_PORT || '50002'
  return `${protocol}//${hostname}:${port}`
}
```

#### Nginx 反向代理配置（相对路径方式）

```nginx
server {
    listen 80;
    server_name _;  # 接受任意域名

    # 前端 UI
    location / {
        proxy_pass http://localhost:50001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端 API - 使用相对路径
    location /api/ {
        proxy_pass http://localhost:50002/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket - 自动检测域名
    location /ws {
        proxy_pass http://localhost:50003/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

#### 优点

1. **无需配置域名**: 自动检测当前访问的域名
2. **支持任意域名**: 无需修改配置即可部署到不同域名
3. **支持 HTTPS**: 自动检测协议（HTTP/HTTPS）
4. **简化部署**: 一套配置适用所有场景

#### 使用场景

- 不知道最终部署的域名
- 需要在多个域名上部署
- 使用云平台的临时域名
- 需要快速迁移到新域名

---

## 8. 启动脚本示例

### 持久化启动脚本（参考 video2sop）

```bash
#!/bin/bash

echo "🚀 启动 ResearchMind 服务..."

# 设置工作目录
cd /path/to/researchmind

# 停止旧进程
echo "📋 停止旧进程..."
pkill -f "python main.py" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null

# 清理端口占用
echo "🔍 检查端口占用..."
for port in 50001 50002 50003 50004 50005 50006; do
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        echo "⚠️  端口 $port 被占用，正在清理..."
        PID=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$PID" ]; then
            kill -9 $PID 2>/dev/null || true
        fi
    fi
done

# 等待进程完全停止
sleep 3

# 创建日志目录
mkdir -p logs

# 配置环境变量
export RESEARCHMIND_HTTP_HOST=0.0.0.0
export RESEARCHMIND_HTTP_PORT=50002
export RESEARCHMIND_WS_HOST=0.0.0.0
export RESEARCHMIND_WS_PORT=50003
export VITE_API_URL=/api
export VITE_WS_URL=ws://localhost:50003/ws

# 启动前端
echo "🎨 启动前端服务..."
cd ui
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   前端服务 PID: $FRONTEND_PID"
cd ..

# 等待前端启动
sleep 5

# 启动后端（作为主进程）
echo "🔧 启动后端服务..."
echo ""
echo "🎉 ResearchMind 启动完成！"
echo "📊 服务状态："
echo "   前端: http://localhost:50001"
echo "   API: http://localhost:50002"
echo "   WebSocket: ws://localhost:50003/ws"
echo ""
echo "📝 日志文件："
echo "   前端日志: logs/frontend.log"
echo "   后端日志: 控制台输出"
echo ""

# 启动后端作为主进程
python main.py
```

### 使用方法

```bash
# 赋予执行权限
chmod +x start.sh

# 运行脚本（自动检测域名）
./start.sh
```

---

## 9. 快速开始（推荐）

### 一键部署

```bash
# 克隆项目
git clone <repository-url>
cd ResearchMind

# 赋予执行权限
chmod +x start.sh

# 一键启动（自动配置所有环境）
./start.sh
```

### 访问应用

- **前端**: http://localhost:50001
- **API**: http://localhost:50002
- **WebSocket**: ws://localhost:50003/ws

### 远程访问

使用 Nginx 反向代理，可以在任意域名上访问：

```bash
# 配置 Nginx（参考第 7 章节）
# 然后访问：http://your-domain.com
```

---

## 10. 环境变量快速参考

### 自动域名检测方案（推荐）

```bash
# 后端监听配置
RESEARCHMIND_HTTP_HOST=0.0.0.0
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=0.0.0.0
RESEARCHMIND_WS_PORT=50003

# 前端连接配置 - 自动检测
VITE_API_URL=/api
VITE_WS_URL=ws://localhost:50003/ws
```

### 本地开发

```bash
VITE_API_URL=http://127.0.0.1:50002
VITE_WS_URL=ws://127.0.0.1:50003/ws
```

### 远程部署（指定域名）

```bash
VITE_API_URL=http://your-domain.com:50002
VITE_WS_URL=ws://your-domain.com:50003/ws
```

### 反向代理部署

```bash
VITE_API_URL=http://your-domain.com/api
VITE_WS_URL=ws://your-domain.com/ws
```

