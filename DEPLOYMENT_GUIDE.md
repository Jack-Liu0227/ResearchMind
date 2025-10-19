# ResearchMind 部署指南

## 1. PaperSearch MCP 文件下载URL

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
VITE_API_URL=http://127.0.0.1:50006
```

生成的下载URL：
```
http://127.0.0.1:50006/api/download/papers/large_language_models_(llm)_bf434a7b/search_results_20251019_000938.csv
```

**远程部署环境（.env.bohr）**：
```
VITE_API_URL=http://dyum1393797.bohrium.tech:50006
```

生成的下载URL：
```
http://dyum1393797.bohrium.tech:50006/api/download/papers/large_language_models_(llm)_bf434a7b/search_results_20251019_000938.csv
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

## 5. 环境变量优先级

### 文件下载URL生成优先级

1. **VITE_API_URL**（最高优先级）
   - 前端调用的API地址
   - 用于生成下载URL

2. **RESEARCHMIND_HTTP_HOST + RESEARCHMIND_HTTP_PORT**（备选）
   - 后端HTTP服务的监听地址
   - 仅在VITE_API_URL未设置时使用

### 示例

```python
# 代码中的优先级逻辑
api_base_url = os.getenv("VITE_API_URL")
if not api_base_url:
    http_host = os.getenv("RESEARCHMIND_HTTP_HOST", "127.0.0.1")
    http_port = os.getenv("RESEARCHMIND_HTTP_PORT", "50006")
    if http_host == "0.0.0.0":
        http_host = "127.0.0.1"
    api_base_url = f"http://{http_host}:{http_port}"

download_url = f"{api_base_url}/api/download/{file_path}"
```

