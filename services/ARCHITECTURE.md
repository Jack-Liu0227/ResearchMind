# Services Layer Architecture

> ResearchMind 后端服务层架构详解

## 📖 架构概览

Services层采用**分层架构**和**事件驱动**设计模式，通过WebSocket和HTTP双协议提供实时通信和文件服务。

## 🏗️ 详细架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Communication Layer                         │
│                                                                     │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐   │
│  │  WebSocket Server        │  │    HTTP Server (FastAPI)     │   │
│  │  (websockets library)    │  │                              │   │
│  │                          │  │  Endpoints:                  │   │
│  │  Endpoint:               │  │  - GET /health               │   │
│  │  ws://localhost:8001/ws  │  │  - GET /api/download/{path}  │   │
│  │                          │  │  - POST /api/upload          │   │
│  │  Features:               │  │  - GET /api/images/{path}    │   │
│  │  - Client管理            │  │                              │   │
│  │  - Session映射           │  │  Features:                   │   │
│  │  - 消息广播              │  │  - 文件上传/下载             │   │
│  │  - 心跳检测              │  │  - 静态文件服务              │   │
│  │                          │  │  - CIF解析                   │   │
│  └──────────────────────────┘  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Message Processing Layer                    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Message Handler                           │  │
│  │                                                              │  │
│  │  消息类型:                                                   │  │
│  │  - message: 用户文本消息                                     │  │
│  │  - file_upload: 文件上传通知                                 │  │
│  │  - system: 系统消息                                          │  │
│  │                                                              │  │
│  │  功能:                                                       │  │
│  │  - 消息验证和解析                                            │  │
│  │  - 路由到Agent Coordinator                                   │  │
│  │  - 错误处理                                                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent Orchestration Layer                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Agent Coordinator                         │  │
│  │                                                              │  │
│  │  Components:                                                 │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │  Google ADK Runner                                     │ │  │
│  │  │  - 运行Agent                                           │ │  │
│  │  │  - 管理事件流                                          │ │  │
│  │  │  - 处理工具调用                                        │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │  Session Service (InMemorySessionService)              │ │  │
│  │  │  - 管理对话历史                                        │ │  │
│  │  │  - 维护上下文                                          │ │  │
│  │  │  - Session隔离                                         │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │                                                              │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │  Event Handler                                         │ │  │
│  │  │  - Event: Agent思考过程                                │ │  │
│  │  │  - ToolCall: 工具调用                                  │ │  │
│  │  │  - ToolResult: 工具结果                                │ │  │
│  │  │  - Response: 最终响应                                  │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Processing Layer                       │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Data Processor                            │  │
│  │                                                              │  │
│  │  功能:                                                       │  │
│  │  - 提取文件链接 (CSV, MD, PNG)                              │  │
│  │  - 生成文件元数据                                            │  │
│  │  - 数据格式转换                                              │  │
│  │  - 发送file_metadata消息                                     │  │
│  │                                                              │  │
│  │  正则表达式:                                                 │  │
│  │  - CSV: papers/.*?\.csv                                     │  │
│  │  - MD: papers/.*?\.md                                       │  │
│  │  - PNG: phonon_results/.*?\.png                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Structure Converter                       │  │
│  │                                                              │  │
│  │  功能:                                                       │  │
│  │  - 解析CIF文件                                               │  │
│  │  - 提取晶格参数                                              │  │
│  │  - 提取原子坐标                                              │  │
│  │  - 转换为JSON格式                                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 消息流详解

### 1. 用户消息处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 接收消息                                                │
│                                                                 │
│ UI发送WebSocket消息:                                            │
│ {                                                               │
│   "type": "message",                                            │
│   "content": "计算GaN的热导率",                                 │
│   "session_id": "session_123"                                   │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: WebSocket Server处理                                    │
│                                                                 │
│ - 验证client_id                                                 │
│ - 查找session_id映射                                            │
│ - 转发到Message Handler                                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Message Handler解析                                     │
│                                                                 │
│ - 验证消息格式                                                  │
│ - 提取content和session_id                                       │
│ - 调用Agent Coordinator                                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Agent Coordinator处理                                   │
│                                                                 │
│ - 获取/创建Session                                              │
│ - 调用Google ADK Runner                                         │
│ - 运行Research Coordinator Agent                                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: Agent事件流处理                                         │
│                                                                 │
│ Event 1: Agent思考                                              │
│ → 发送到前端: {"type": "agent_thinking", ...}                   │
│                                                                 │
│ Event 2: 调用Simulation Agent                                   │
│ → 发送到前端: {"type": "tool_call", "tool": "simulation"}       │
│                                                                 │
│ Event 3: MCP Server返回结果                                     │
│ → 发送到前端: {"type": "tool_result", ...}                      │
│                                                                 │
│ Event 4: Agent最终响应                                          │
│ → 发送到前端: {"type": "agent_response", "content": "..."}      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: Data Processor处理                                      │
│                                                                 │
│ - 提取文件链接 (CSV, MD, PNG)                                   │
│ - 生成文件元数据                                                │
│ - 发送file_metadata消息到前端                                   │
│                                                                 │
│ {                                                               │
│   "type": "file_metadata",                                      │
│   "files": [                                                    │
│     {                                                           │
│       "type": "csv",                                            │
│       "url": "http://localhost:8000/api/download/...",          │
│       "filename": "results.csv"                                 │
│     }                                                           │
│   ]                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 7: 前端展示                                                │
│                                                                 │
│ - 显示Agent响应                                                 │
│ - 自动展示CSV/MD文件                                            │
│ - 显示声子谱图片                                                │
│ - 提供下载按钮                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. 文件上传处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 用户上传CIF文件                                         │
│                                                                 │
│ POST /api/upload                                                │
│ Content-Type: multipart/form-data                               │
│ File: structure.cif                                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: HTTP Server接收                                         │
│                                                                 │
│ - 验证文件类型 (.cif)                                           │
│ - 检查文件大小 (<10MB)                                          │
│ - 保存到临时目录                                                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Structure Converter解析                                 │
│                                                                 │
│ - 读取CIF文件                                                   │
│ - 提取晶格参数 (a, b, c, alpha, beta, gamma)                   │
│ - 提取原子坐标 (element, x, y, z)                               │
│ - 生成JSON格式                                                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 返回结构信息                                            │
│                                                                 │
│ {                                                               │
│   "formula": "GaN",                                             │
│   "lattice": {...},                                             │
│   "atoms": [...],                                               │
│   "file_path": "/tmp/structure.cif"                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: 前端显示结构                                            │
│                                                                 │
│ - 3D可视化 (Three.js)                                           │
│ - 显示晶格参数                                                  │
│ - 显示原子列表                                                  │
│ - 提供"使用此结构"按钮                                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: 用户确认使用                                            │
│                                                                 │
│ 发送WebSocket消息:                                              │
│ {                                                               │
│   "type": "file_upload",                                        │
│   "file_path": "/tmp/structure.cif",                            │
│   "action": "calculate_kappa"                                   │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 7: Agent处理                                               │
│                                                                 │
│ - Message Handler接收file_upload消息                            │
│ - Agent Coordinator调用Simulation Agent                         │
│ - Simulation Agent使用上传的CIF文件进行计算                     │
└─────────────────────────────────────────────────────────────────┘
```

## 🔌 通信协议

### WebSocket协议

**连接URL**: `ws://localhost:8001/ws/{client_id}`

**消息格式**:
```json
{
  "type": "message|file_upload|system",
  "content": "消息内容",
  "session_id": "session_123",
  "timestamp": "2025-10-15T10:00:00Z"
}
```

**响应格式**:
```json
{
  "type": "agent_response|agent_thinking|tool_call|tool_result|file_metadata",
  "content": "响应内容",
  "session_id": "session_123",
  "timestamp": "2025-10-15T10:00:01Z"
}
```

### HTTP协议

**文件下载**:
```
GET /api/download/{file_path}
Response: File content
Content-Type: text/csv | text/markdown | application/x-cif
```

**文件上传**:
```
POST /api/upload
Content-Type: multipart/form-data
Response: JSON (structure info)
```

**静态文件**:
```
GET /api/images/{file_path}
Response: Image file
Content-Type: image/png
```

## 📊 Session管理

### Session生命周期

```
创建Session
  ↓
用户发送消息
  ↓
Session记录消息历史
  ↓
Agent处理并响应
  ↓
Session记录响应
  ↓
30分钟无活动
  ↓
Session过期并清理
```

### Session数据结构

```python
{
  "session_id": "session_123",
  "client_id": "client_456",
  "created_at": "2025-10-15T10:00:00Z",
  "last_activity": "2025-10-15T10:30:00Z",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "agent", "content": "..."}
  ]
}
```

## 🔒 安全性设计

### 文件访问控制

```python
# 仅允许访问papers目录
ALLOWED_DIRECTORIES = [
    "mcp_servers/paper_search/papers",
    "mcp_servers/simulation/phonon_results"
]

# 路径规范化
file_path = file_path.replace('\\', '/').lstrip('./')

# 安全性检查
if not any(file_path.startswith(d) for d in ALLOWED_DIRECTORIES):
    raise HTTPException(403, "Access denied")
```

### CORS配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 文件大小限制

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

## 📈 性能优化

### 异步处理

所有I/O操作使用`async/await`:
```python
async def handle_connection(websocket: WebSocket, client_id: str)
async def process_message(session_id: str, message: str)
async def send_message(client_id: str, message: dict)
```

### 连接池

- WebSocket连接池: 100+并发连接
- HTTP连接复用

### 缓存策略

- Session缓存: 内存缓存
- 静态文件缓存: 浏览器缓存

## 🧪 测试策略

### 单元测试

- Message Handler测试
- Data Processor测试
- Structure Converter测试

### 集成测试

- WebSocket连接测试
- HTTP API测试
- Agent Coordinator测试

### 端到端测试

- 完整消息流程测试
- 文件上传/下载测试

## 📚 相关文档

- [README.md](./README.md) - Services使用文档
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - 系统整体架构
- [../agents/ARCHITECTURE.md](../agents/ARCHITECTURE.md) - Agents架构

## 📄 许可证

MIT License

