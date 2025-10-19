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

