# Services Layer

> ResearchMind 后端服务层 - 连接前端UI和Google ADK Agents的桥梁

## 📖 概述

Services层是ResearchMind系统的核心后端服务层，负责：
- 管理WebSocket和HTTP通信
- 协调Google ADK Agents
- 处理消息路由和数据转换
- 提供文件上传/下载服务
- 管理Session状态

## 🏗️ 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (UI)                          │
│                   Port: 5173                                │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼ WebSocket             ▼ HTTP
┌──────────────────────────┐  ┌──────────────────────────┐
│  WebSocket Server        │  │    HTTP Server           │
│  Port: 8001              │  │    Port: 8000            │
│                          │  │                          │
│  - Client管理            │  │  - REST API              │
│  - 消息路由              │  │  - 文件上传/下载          │
│  - Session管理           │  │  - 静态文件服务           │
└──────────────────────────┘  └──────────────────────────┘
                │                       │
                └───────────┬───────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │      Message Handler                  │
        │  - 消息解析                           │
        │  - 路由到Agent Coordinator            │
        │  - 文件上传处理                       │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │      Agent Coordinator                │
        │  - Google ADK Runner                  │
        │  - Session Service                    │
        │  - Agent事件处理                      │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │      Data Processor                   │
        │  - 数据转换                           │
        │  - 文件链接提取                       │
        │  - 元数据生成                         │
        └───────────────────────────────────────┘
                            │
                            ▼
                    Google ADK Agents
```

## 📁 文件结构

```
services/
├── __init__.py
├── websocket_server.py      # WebSocket服务器
├── http_server.py            # HTTP服务器
├── agent_coordinator.py      # Agent协调器
├── message_handler.py        # 消息处理器
├── data_processor.py         # 数据处理器
├── structure_converter.py    # CIF结构转换器
├── static_file_service.py    # 静态文件服务
├── config.py                 # 配置文件
└── README.md                 # 本文档
```

## 🔧 核心组件

### 1. WebSocket Server (`websocket_server.py`)

**职责**:
- 管理WebSocket客户端连接
- 维护客户端Session映射
- 路由消息到Message Handler
- 实时推送Agent响应到前端

**关键功能**:
```python
class WebSocketServer:
    async def handle_connection(websocket: WebSocket, client_id: str)
    async def send_message(client_id: str, message: dict)
    async def broadcast(message: dict)
```

**端口**: 8001

**消息格式**:
```json
{
  "type": "message",
  "content": "用户输入",
  "session_id": "session_123"
}
```

### 2. HTTP Server (`http_server.py`)

**职责**:
- 提供REST API端点
- 处理文件上传/下载
- 提供静态文件服务（图片、CSV、MD）
- CIF文件解析和验证

**关键端点**:

#### 文件下载
```
GET /api/download/{file_path}
```
- 支持CSV、MD、CIF文件下载
- 自动路径规范化
- 安全性检查（仅允许papers目录）

#### 文件上传
```
POST /api/upload
```
- 支持CIF文件上传
- 自动验证和解析
- 返回结构信息

#### 静态文件
```
GET /api/images/{file_path}
```
- 提供声子谱图片
- 提供晶体结构图片

#### 健康检查
```
GET /health
```

**端口**: 8000

### 3. Agent Coordinator (`agent_coordinator.py`)

**职责**:
- 协调Google ADK Agents
- 管理Session Service (InMemorySessionService)
- 运行Google ADK Runner
- 处理Agent事件流
- 转发Agent响应到WebSocket

**关键功能**:
```python
class AgentCoordinator:
    async def process_message(session_id: str, message: str)
    async def _handle_agent_events(session_id: str, event_stream)
    async def _send_to_websocket(client_id: str, message: dict)
```

**Agent事件类型**:
- `Event`: Agent思考过程
- `ToolCall`: 工具调用
- `ToolResult`: 工具返回结果
- `Response`: Agent最终响应

### 4. Message Handler (`message_handler.py`)

**职责**:
- 解析WebSocket消息
- 路由到Agent Coordinator
- 处理文件上传消息
- 发送响应消息

**消息类型**:
- `message`: 用户文本消息
- `file_upload`: 文件上传通知
- `system`: 系统消息

### 5. Data Processor (`data_processor.py`)

**职责**:
- 处理Agent响应数据
- 提取文件链接（CSV、MD、PNG）
- 生成文件元数据
- 发送file_metadata消息到前端

**关键功能**:
```python
class DataProcessor:
    def process_agent_response(response: str) -> dict
    def _extract_file_links(text: str) -> List[dict]
    def _process_file_links(files: List[dict], client_id: str)
```

**文件元数据格式**:
```json
{
  "type": "file_metadata",
  "files": [
    {
      "type": "csv",
      "url": "http://localhost:8000/api/download/papers/.../file.csv",
      "filename": "file.csv"
    }
  ]
}
```

### 6. Structure Converter (`structure_converter.py`)

**职责**:
- 解析CIF文件
- 转换为前端可用的JSON格式
- 提取晶体学信息（晶格参数、原子坐标）

**输出格式**:
```json
{
  "formula": "NaCl",
  "lattice": {
    "a": 5.64, "b": 5.64, "c": 5.64,
    "alpha": 90, "beta": 90, "gamma": 90
  },
  "atoms": [
    {"element": "Na", "x": 0.0, "y": 0.0, "z": 0.0},
    {"element": "Cl", "x": 0.5, "y": 0.5, "z": 0.5}
  ]
}
```

### 7. Static File Service (`static_file_service.py`)

**职责**:
- 配置静态文件挂载
- 管理文件访问权限
- 提供文件路径映射

**挂载路径**:
```python
# 声子谱图片
app.mount("/api/images/phonon_results", 
          StaticFiles(directory="mcp_servers/simulation/phonon_results"))

# 论文相关文件
app.mount("/api/download/papers", 
          StaticFiles(directory="mcp_servers/paper_search/papers"))
```

## 🔄 数据流

### 1. 用户消息流程

```
用户输入 "计算GaN的热导率"
  ↓
UI发送WebSocket消息
  ↓
WebSocket Server接收
  ↓
Message Handler解析
  ↓
Agent Coordinator处理
  ↓
调用Research Coordinator Agent
  ↓
Agent决策调用Simulation Agent
  ↓
Simulation Agent调用MCP Server
  ↓
MCP Server执行计算
  ↓
返回结果 (包含文件路径)
  ↓
Data Processor提取文件链接
  ↓
发送file_metadata到前端
  ↓
前端自动展示文件
```

### 2. 文件上传流程

```
用户上传CIF文件
  ↓
HTTP Server /api/upload
  ↓
Structure Converter解析CIF
  ↓
返回结构信息
  ↓
前端显示结构
  ↓
用户确认后发送消息
  ↓
Message Handler处理file_upload消息
  ↓
Agent Coordinator接收文件路径
  ↓
调用Simulation Agent处理
```

## 🚀 启动和配置

### 环境变量

```bash
# .env
MODEL_USE=gemini/gemini-2.5-flash
PAPER_SEARCH_MCP_URL=http://localhost:50001/sse
DATABASE_MCP_URL=http://localhost:5002/sse
SIMULATION_MCP_URL=http://localhost:5003/sse
```

### 启动命令

```bash
# 启动所有服务
uv run python main.py
```

这将同时启动：
- WebSocket Server (Port 8002)
- HTTP Server (Port 8000)
- Agent Coordinator

### 日志配置

日志级别: INFO
日志格式: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

## 🧪 测试

### WebSocket连接测试

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8001/ws/test_client"
    async with websockets.connect(uri) as websocket:
        message = {
            "type": "message",
            "content": "你好",
            "session_id": "test_session"
        }
        await websocket.send(json.dumps(message))
        response = await websocket.recv()
        print(response)

asyncio.run(test_websocket())
```

### HTTP API测试

```bash
# 健康检查
curl http://localhost:8000/health

# 文件下载
curl -O http://localhost:8000/api/download/papers/test/file.csv

# 文件上传
curl -X POST -F "file=@structure.cif" http://localhost:8000/api/upload
```

## 📊 性能指标

- **WebSocket连接**: 支持100+并发连接
- **消息延迟**: <100ms (本地)
- **文件上传**: 最大10MB
- **Session超时**: 30分钟无活动

## 🔒 安全性

- **文件访问**: 仅允许访问papers目录
- **路径规范化**: 防止路径遍历攻击
- **CORS**: 配置允许的源
- **文件大小限制**: 防止DoS攻击

## 📚 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Services架构详解
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - 系统整体架构
- [../agents/README.md](../agents/README.md) - Agents文档

## 📄 许可证

MIT License

