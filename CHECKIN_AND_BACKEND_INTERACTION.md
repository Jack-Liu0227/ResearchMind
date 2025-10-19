# ResearchMind 签到和后端交互服务说明

## 1. 系统架构概览

ResearchMind 采用前后端分离架构，通过 WebSocket 和 HTTP 两种方式进行通信：

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (React + TypeScript)                │
│                    Port 50001 (0.0.0.0)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    HTTP API        WebSocket         MCP Services
    Port 50002      Port 50003        (50004/50005/50006)
    (127.0.0.1)     (127.0.0.1)       (127.0.0.1)
```

---

## 2. 客户端签到流程

### 2.1 连接建立

当用户打开前端应用时，会自动建立 WebSocket 连接：

```typescript
// ui/src/services/websocket.ts
const ws = new WebSocket(`ws://${host}:${port}/${clientId}`)
```

**流程**：
1. 前端生成唯一的 `clientId`（UUID）
2. 建立 WebSocket 连接到后端
3. 后端接收连接请求

### 2.2 服务器端处理

```python
# services/websocket_server.py
async def handle_client(self, websocket, path):
    client_id = str(uuid.uuid4())
    self.connected_clients[client_id] = websocket
    
    # 发送欢迎消息
    await self.message_handler.send_message(websocket, "connected", {
        "clientId": client_id,
        "message": "Connected to ResearchMind",
        "timestamp": datetime.now().isoformat()
    })
    
    # 发送可用的Agent列表
    await self.message_handler.send_agent_list(websocket)
```

### 2.3 签到消息格式

**客户端发送的签到消息**：
```json
{
  "type": "connected",
  "clientId": "uuid-string",
  "timestamp": "2025-10-19T14:00:00"
}
```

**服务器响应**：
```json
{
  "type": "connected",
  "clientId": "uuid-string",
  "message": "Connected to ResearchMind",
  "timestamp": "2025-10-19T14:00:00"
}
```

---

## 3. 会话管理

### 3.1 会话创建

每个客户端连接时，后端会创建一个会话：

```python
# services/session_manager.py
@classmethod
def create_session(
    cls,
    session_id: str,
    client_id: str,
    agent_id: Optional[str] = None,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """创建新会话"""
    session_data = {
        "session_id": session_id,
        "client_id": client_id,
        "agent_id": agent_id,
        "title": title or f"Session {session_id[:8]}",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "message_count": 0,
        "structure_count": 0,
        "image_count": 0
    }
```

### 3.2 会话存储

会话数据存储在本地文件系统中：

```
data/
├── sessions/
│   ├── session_id_1/
│   │   ├── structures/
│   │   └── images/
│   └── session_id_2/
├── metadata/
│   ├── session_id_1.json
│   └── session_id_2.json
└── registry.json
```

---

## 4. 消息处理流程

### 4.1 消息类型

```python
# services/message_handler.py
self.message_handlers = {
    "chat": self.handle_chat_message,
    "message": self.handle_chat_message,
    "upload_structure": self.handle_upload_structure,
    "upload_structures": self.handle_upload_structures,
    "ping": self.handle_ping,
}
```

### 4.2 聊天消息处理

**客户端发送**：
```json
{
  "type": "chat",
  "content": "计算GaN的热导率",
  "agentId": "simulation_agent",
  "sessionId": "session_123"
}
```

**处理流程**：
```
1. MessageHandler.handle_chat_message()
   ↓
2. AgentCoordinator.process_chat_message()
   ↓
3. 选择对应的Agent（Simulation/Database/PaperSearch）
   ↓
4. Agent调用MCP工具
   ↓
5. 返回结果给前端
```

### 4.3 文件上传处理

**客户端发送**：
```json
{
  "type": "upload_structure",
  "structure": {
    "id": "struct_123",
    "formula": "GaN",
    "latticeParameters": {...},
    "atoms": [...]
  }
}
```

**处理流程**：
```
1. MessageHandler.handle_upload_structure()
   ↓
2. DataProcessor.process_uploaded_structure()
   ↓
3. StructureConverter.convert_to_conventional()
   ↓
4. 保存结构数据
   ↓
5. 返回成功消息
```

---

## 5. 后端交互服务

### 5.1 HTTP API 端点

**基础URL**: `http://127.0.0.1:50002` (本地) 或 `http://域名:50002` (远程)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/service_status` | GET | 服务状态 |
| `/api/upload/structure` | POST | 上传单个结构 |
| `/api/upload/structures` | POST | 上传多个结构 |
| `/api/parse_cif` | POST | 解析CIF文件 |
| `/api/convert_to_conventional` | POST | 转换为常规晶胞 |
| `/api/phonon_results` | GET | 获取声子结果 |
| `/api/generated_structures` | GET | 获取生成的结构 |
| `/api/images/{type}/{filename}` | GET | 获取图片 |
| `/api/download/{file_path}` | GET | 下载文件 |

### 5.2 WebSocket 端点

```
ws://host:port/{clientId}
```

**连接参数**：
- `host`: WebSocket服务器地址（127.0.0.1或域名）
- `port`: WebSocket服务器端口（50003）
- `clientId`: 客户端唯一标识符

### 5.3 MCP 服务调用

后端通过 MCP 工具调用三个主要服务：

**1. Database MCP (Port 50006)**
- 查询Materials Project、OQMD、COD、AFLOW数据库
- 生成晶体结构

**2. Paper Search MCP (Port 50004)**
- 搜索学术论文
- 生成搜索报告

**3. Simulation MCP (Port 50005)**
- 计算晶体结构能量
- 计算声子谱
- 执行结构弛豫

---

## 6. 数据流示例

### 6.1 用户输入到结果返回

```
用户输入: "计算GaN的热导率"
  ↓
前端发送WebSocket消息
  ↓
MessageHandler.handle_chat_message()
  ↓
AgentCoordinator.process_chat_message()
  ↓
选择Simulation Agent
  ↓
Agent调用MCP工具
  ↓
MatterSim计算热导率
  ↓
返回结果（包含文件路径）
  ↓
DataProcessor提取文件链接
  ↓
发送file_metadata到前端
  ↓
前端自动展示结果
```

### 6.2 文件上传到处理完成

```
用户上传CIF文件
  ↓
前端发送upload_structure消息
  ↓
MessageHandler.handle_upload_structure()
  ↓
DataProcessor.process_uploaded_structure()
  ↓
StructureConverter.convert_to_conventional()
  ↓
保存结构数据到本地
  ↓
返回upload_success消息
  ↓
前端显示结构信息
```

---

## 7. 错误处理

### 7.1 连接错误

```python
# 自动重连机制
if connection_lost:
    retry_count = 0
    while retry_count < max_retries:
        try:
            reconnect()
            break
        except:
            retry_count += 1
            wait(exponential_backoff)
```

### 7.2 消息错误

```python
# 发送错误消息给客户端
await self.send_error(websocket, "Error message")
```

---

## 8. 性能优化

### 8.1 连接池

```python
# HTTP客户端连接池
http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=5,
        max_connections=10
    )
)
```

### 8.2 超时配置

```python
# WebSocket超时
timeout_keep_alive=300  # 5分钟

# HTTP超时
timeout=httpx.Timeout(300.0, connect=30.0)
```

### 8.3 并发限制

```python
# 限制并发连接数
limit_concurrency=100
backlog=2048
```

---

## 9. 安全性

### 9.1 文件访问控制

```python
# 仅允许访问特定目录
ALLOWED_DIRECTORIES = [
    "mcp_servers/paper_search/papers",
    "mcp_servers/simulation/phonon_results"
]
```

### 9.2 路径规范化

```python
# 防止路径遍历攻击
file_path = file_path.replace('\\', '/').lstrip('./')
```

### 9.3 CORS配置

```python
# 允许特定来源的跨域请求
CORSMiddleware(
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

---

## 10. 调试和监控

### 10.1 健康检查

```bash
# HTTP健康检查
curl http://localhost:50002/health

# WebSocket连接测试
wscat -c ws://localhost:50003/test-client-id
```

### 10.2 日志查看

```bash
# 后端日志
tail -f logs/backend.log

# WebSocket日志
tail -f logs/websocket.log

# MCP服务日志
tail -f logs/database.log
tail -f logs/paper_search.log
tail -f logs/simulation.log
```

### 10.3 性能监控

- 响应时间监控
- 内存使用监控
- 活跃连接数监控
- 消息处理速率监控

---

## 11. 自动域名检测和反向代理支持

### 11.1 前端自动域名检测

前端会自动检测当前访问的域名，无需在环境变量中指定具体的域名。

#### 工作原理

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

#### 环境变量配置

```bash
# 后端监听配置 - 监听所有接口
RESEARCHMIND_HTTP_HOST=0.0.0.0
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=0.0.0.0
RESEARCHMIND_WS_PORT=50003

# 前端连接配置 - 使用相对路径（自动检测）
VITE_API_URL=/api
VITE_WS_URL=ws://localhost:50003/ws
```

### 11.2 后端 URL 生成

后端在生成文件下载 URL 时，也支持相对路径和自动检测：

```python
# mcp_servers/paper_search/server.py
def get_api_base_url() -> str:
    """
    获取 API 基础 URL，支持多种配置方式

    优先级：
    1. VITE_API_URL（前端调用的API地址）
    2. RESEARCHMIND_HTTP_HOST + RESEARCHMIND_HTTP_PORT
    """
    api_url = os.getenv("VITE_API_URL")

    if api_url:
        # 如果是相对路径，需要转换为完整 URL
        if api_url.startswith('/'):
            # 相对路径：直接返回，前端会处理
            return api_url
        else:
            # 完整 URL：直接返回
            return api_url

    # 备选方案：使用 RESEARCHMIND_HTTP_HOST + RESEARCHMIND_HTTP_PORT
    http_host = os.getenv("RESEARCHMIND_HTTP_HOST", "127.0.0.1")
    http_port = os.getenv("RESEARCHMIND_HTTP_PORT", "50002")

    # 如果监听地址是 0.0.0.0，使用 localhost 以支持反向代理
    if http_host == "0.0.0.0":
        http_host = "localhost"

    return f"http://{http_host}:{http_port}"
```

### 11.3 Nginx 反向代理配置

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

### 11.4 部署流程

#### 步骤1：配置环境变量

```bash
# .env 文件
RESEARCHMIND_HTTP_HOST=0.0.0.0
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=0.0.0.0
RESEARCHMIND_WS_PORT=50003
VITE_API_URL=/api
VITE_WS_URL=ws://localhost:50003/ws
```

#### 步骤2：启动应用

```bash
# 一键启动
chmod +x start.sh
./start.sh
```

#### 步骤3：配置 Nginx

```bash
# 复制 Nginx 配置
sudo cp nginx.conf /etc/nginx/sites-available/researchmind
sudo ln -s /etc/nginx/sites-available/researchmind /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 步骤4：访问应用

```bash
# 本地访问
http://localhost:50001

# 远程访问（通过 Nginx）
http://your-domain.com
```

### 11.5 优点总结

1. **无需配置域名** - 自动检测当前访问的域名
2. **支持任意域名** - 无需修改配置即可部署到不同域名
3. **支持 HTTPS** - 自动检测协议（HTTP/HTTPS）
4. **简化部署** - 一套配置适用所有场景
5. **灵活迁移** - 轻松迁移到新域名无需修改代码
6. **安全性** - 后端服务不直接暴露，通过反向代理访问

