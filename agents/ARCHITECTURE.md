# ResearchMind System Architecture

## 系统概览

ResearchMind 是一个基于 Google ADK (Agent Development Kit) 的多代理系统，采用分层架构设计，通过 MCP (Model Context Protocol) 连接各个功能模块。

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interface                              │
│                    (WebSocket + React Frontend)                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      WebSocket Server                               │
│                    (server.py - Port 8002)                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │           Google ADK Runner + Session Service                │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Research Coordinator Agent                        │
│                  (agents/agent.py - LlmAgent)                       │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Prompt: RESEARCH_COORDINATOR_PROMPT                         │ │
│  │  Model: gemini/gemini-2.5-flash (LiteLLM)                    │ │
│  │  Tools: [deep_research, database, simulation] (AgentTool)    │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Deep Research    │  │   Database       │  │   Simulation     │
│     Agent        │  │    Agent         │  │     Agent        │
│                  │  │                  │  │                  │
│ (Google ADK      │  │ (Google ADK      │  │ (Google ADK      │
│  Agent)          │  │  Agent)          │  │  Agent)          │
│                  │  │                  │  │                  │
│ Tools:           │  │ Tools:           │  │ Tools:           │
│ - MCPToolset     │  │ - MCPToolset     │  │ - MCPToolset     │
│                  │  │ - AgentTool      │  │                  │
│                  │  │   (simulation)   │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Paper Search     │  │ Materials DB     │  │  Simulation      │
│  MCP Server      │  │  MCP Server      │  │  MCP Server      │
│                  │  │                  │  │                  │
│ Port: 50001      │  │ Port: 5002       │  │ Port: 5003       │
│ Protocol: SSE    │  │ Protocol: SSE    │  │ Protocol: SSE    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## 核心组件

### 1. Research Coordinator Agent

**文件**: `agents/agent.py`

**类型**: `LlmAgent` (Google ADK)

**职责**:
- 接收用户请求
- 智能分析请求类型
- 决策调用哪个子代理
- 协调多个子代理完成复杂任务
- 整合结果并返回

**关键代码**:
```python
research_coordinator = LlmAgent(
    name="research_coordinator",
    model=MODEL,
    description="Coordinating materials science research...",
    instruction=RESEARCH_COORDINATOR_PROMPT,
    output_key="research_query",
    tools=[
        AgentTool(agent=literature_agent),
        AgentTool(agent=database_agent),
        AgentTool(agent=simulation_agent),
    ],
)
```

**提示词**: `agents/prompt.py` - `RESEARCH_COORDINATOR_PROMPT`

**决策逻辑**:
```python
# 文献研究类请求
if "文献" in query or "论文" in query or "综述" in query:
    call deep_research_agent

# 材料结构查询类请求
elif "晶体结构" in query or "CIF" in query or "数据库" in query:
    call database_agent

# 性能计算类请求
elif "热导率" in query or "能量" in query or "仿真" in query:
    call database_agent  # 先获取结构
    call simulation_agent  # 再计算

# 综合研究类请求
else:
    call deep_research_agent
    call database_agent
    call simulation_agent
```

### 2. Deep Research Agent

**文件**: `agents/deep_research/agent.py`

**类型**: `Agent` (Google ADK)

**职责**:
- 协调 4 个子代理（Search, Paper Manager, Report Generator, Context Manager）
- 多源搜索（ArXiv + Tavily）
- 论文分析和总结
- 生成研究报告
- 向量化存储和语义搜索

**架构**:
```python
class DeepResearchAgent(BaseAgent):
    def __init__(self):
        # 创建 MCP Toolset
        mcp_toolset = MCPToolset(
            connection_params=SseServerParams(url=MCP_URL)
        )
        
        # 引用子代理
        self._search_agent = search_agent
        self._paper_manager_agent = paper_manager_agent
        self._report_generator_agent = report_generator_agent
        self._context_manager_agent = context_manager_agent
        
        # 创建主代理
        self._main_agent = Agent(
            name="research_assistant",
            model=LiteLlm(model=model_name),
            instruction=get_main_agent_instruction(),
            tools=[
                mcp_toolset,
                AgentTool(agent=search_agent),
                AgentTool(agent=paper_manager_agent),
                AgentTool(agent=report_generator_agent),
                AgentTool(agent=context_manager_agent)
            ]
        )
```

**子代理**:
1. **Search Agent**: 多源搜索
2. **Paper Manager Agent**: 论文管理和表格生成
3. **Report Generator Agent**: 报告生成
4. **Context Manager Agent**: 向量化和语义搜索

**详细文档**: [deep_research/ARCHITECTURE.md](./deep_research/ARCHITECTURE.md)

### 3. Database Agent

**文件**: `agents/database_agent/agent.py`

**类型**: `Agent` (Google ADK)

**职责**:
- 查询多个材料数据库（MP, OQMD, COD, AFLOW）
- 获取晶体结构和材料属性
- **自动结构生成**：数据库查询失败时自动调用 Simulation Agent

**架构**:
```python
root_agent = Agent(
    name="database_agent",
    model=LiteLlm(model=MODEL),
    instruction=INSTRUCTION,
    tools=[
        toolset,  # MCP Toolset
        AgentTool(agent=simulation_agent)  # 自动结构生成
    ]
)
```

**工作流程**:
```
1. 验证化学式
2. 按优先级查询数据库：MP → OQMD → COD → AFLOW
3. 如果所有数据库都失败：
   a. 通知用户："正在自动生成结构..."
   b. 调用 simulation_agent(composition)
   c. 返回生成的 CIF
4. 格式化输出
```

**详细文档**: [database_agent/ARCHITECTURE.md](./database_agent/ARCHITECTURE.md)

### 4. Simulation Agent

**文件**: `agents/simulation_agent/agent.py`

**类型**: `Agent` (Google ADK)

**职责**:
- 晶体结构生成（CrystaLLM）
- 热导率计算（AI4Kappa）
- 能量属性预测（MatterSim）
- DFT 和分子动力学设置

**架构**:
```python
root_agent = Agent(
    name="simulation_agent",
    model=LiteLlm(model=MODEL),
    instruction=SIMULATION_AGENT_INSTRUCTION,
    tools=[toolset]  # MCP Toolset
)
```

**详细文档**: [simulation_agent/ARCHITECTURE.md](./simulation_agent/ARCHITECTURE.md)

## MCP 服务器

### 1. Paper Search MCP Server

**文件**: `mcp_servers/paper_search/server.py`

**端口**: 50001

**工具数量**: 18

**工具分类**:
- Search Agent: 7 tools
- Paper Manager: 5 tools
- Report Generator: 1 tool
- Context Manager: 4 tools
- Shared: 1 tool

**详细文档**: [mcp_servers/paper_search/ARCHITECTURE.md](../mcp_servers/paper_search/ARCHITECTURE.md)

### 2. Materials Database MCP Server

**文件**: `mcp_servers/database_call/server.py`

**端口**: 5002

**工具数量**: 5

**工具列表**:
- `materials_project_query_tool`
- `get_oqmd_phases`
- `search_cod_by_formula`
- `get_aflow_data`
- `TavilySearch`

**详细文档**: [mcp_servers/database_call/ARCHITECTURE.md](../mcp_servers/database_call/ARCHITECTURE.md)

### 3. Simulation MCP Server

**文件**: `mcp_servers/simulation/server.py`

**端口**: 5003

**工具数量**: 7

**工具列表**:
- `generate_crystal_structure`
- `extract_and_validate_cif`
- `validate_cif_content`
- `calculate_kappa_from_cif`
- `calculate_energy_from_cif`
- `setup_vasp_calculation`
- `setup_gaussian_calculation`
- `setup_lammps_simulation`

**详细文档**: [mcp_servers/simulation/ARCHITECTURE.md](../mcp_servers/simulation/ARCHITECTURE.md)

## 数据流

### 完整研究流程

```
用户："研究 GaN 的热导率"
    │
    ▼
WebSocket Server 接收请求
    │
    ▼
创建 ADK Runner 和 Session
    │
    ▼
调用 Research Coordinator Agent
    │
    ▼
分析请求 → 决策：综合研究类
    │
    ├─→ 调用 deep_research_agent
    │   │
    │   ├─→ 调用 search_agent("GaN 热导率")
    │   │   └─→ Paper Search MCP Server
    │   │       ├─→ search_arxiv_papers
    │   │       └─→ tavily_academic_search
    │   │
    │   ├─→ 调用 paper_manager_agent("分析论文")
    │   │   └─→ Paper Search MCP Server
    │   │       └─→ batch_paper_analysis
    │   │
    │   └─→ 返回文献综述
    │
    ├─→ 调用 database_agent("GaN")
    │   │
    │   ├─→ Materials Database MCP Server
    │   │   ├─→ materials_project_query_tool("GaN") → 失败
    │   │   ├─→ get_oqmd_phases("GaN") → 失败
    │   │   ├─→ search_cod_by_formula("Ga N") → 失败
    │   │   └─→ get_aflow_data("GaN") → 失败
    │   │
    │   ├─→ 所有数据库都失败
    │   │
    │   └─→ 调用 simulation_agent("GaN")
    │       └─→ Simulation MCP Server
    │           └─→ generate_crystal_structure("GaN")
    │               └─→ 返回 CIF
    │
    ├─→ 调用 simulation_agent("计算热导率")
    │   │
    │   └─→ Simulation MCP Server
    │       └─→ calculate_kappa_from_cif(cif_content)
    │           └─→ 返回热导率值
    │
    └─→ 整合结果
        │
        └─→ 返回给用户：
            - 文献背景
            - 结构信息（生成的 CIF）
            - 热导率计算结果
            - 综合分析
```

## 通信协议

### WebSocket 协议

**端口**: 8002

**消息格式**:
```json
{
    "type": "chat",
    "content": "用户消息",
    "agentId": "research_coordinator",
    "sessionId": "session_123"
}
```

**响应格式**:
```json
{
    "type": "message",
    "content": "Agent 响应",
    "agentId": "research_coordinator",
    "timestamp": "2025-10-07T01:30:00"
}
```

### MCP 协议 (Server-Sent Events)

**协议**: SSE (Server-Sent Events)

**请求格式**:
```json
{
    "tool": "materials_project_query_tool",
    "args": {
        "formula": "LiFePO4",
        "num_return": 3
    }
}
```

**响应格式**:
```json
{
    "status": "success",
    "result": "..."
}
```

## 错误处理

### 1. Agent 级别错误处理

```python
try:
    result = agent.run(query)
except Exception as e:
    logger.error("Agent execution failed", error=str(e))
    return {
        "status": "error",
        "error": str(e)
    }
```

### 2. MCP 工具级别错误处理

```python
@app.tool
async def tool_function(...):
    try:
        # 工具逻辑
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### 3. WebSocket 级别错误处理

```python
try:
    async for event in runner.run(...):
        # 处理事件
except Exception as e:
    await send_error(websocket, str(e))
```

## 性能优化

### 1. 异步处理
- 所有 MCP 工具都是异步函数
- WebSocket 服务器使用异步 I/O
- 支持并发请求

### 2. Session 管理
- 使用 `InMemorySessionService` 管理会话
- 每个用户有独立的 session
- 支持会话状态持久化

### 3. 连接池
- MCP 服务器使用连接池
- 减少重复连接开销

## 扩展性

### 添加新 Agent

1. **创建 Agent 文件**:
```python
# agents/new_agent/agent.py
root_agent = Agent(
    name="new_agent",
    model=LiteLlm(model=MODEL),
    instruction=INSTRUCTION,
    tools=[toolset]
)
```

2. **在 Research Coordinator 中注册**:
```python
# agents/agent.py
from .new_agent.agent import root_agent as new_agent

research_coordinator = LlmAgent(
    ...
    tools=[
        ...,
        AgentTool(agent=new_agent)
    ]
)
```

3. **更新提示词**:
```python
# agents/prompt.py
RESEARCH_COORDINATOR_PROMPT = """
...
4. **new_agent**: 新功能描述
...
"""
```

### 添加新 MCP Server

1. **创建 MCP Server**:
```python
# mcp_servers/new_server/server.py
from fastmcp import FastMCP

app = FastMCP("new_server")

@app.tool
async def new_tool(...):
    """新工具"""
    return result
```

2. **在 Agent 中连接**:
```python
toolset = MCPToolset(
    connection_params=SseServerParams(
        url="http://localhost:5004/sse"
    )
)
```

## 相关文档

- [Deep Research Agent](./deep_research/ARCHITECTURE.md)
- [Database Agent](./database_agent/ARCHITECTURE.md)
- [Simulation Agent](./simulation_agent/ARCHITECTURE.md)
- [Paper Search MCP Server](../mcp_servers/paper_search/ARCHITECTURE.md)
- [Materials Database MCP Server](../mcp_servers/database_call/ARCHITECTURE.md)
- [Simulation MCP Server](../mcp_servers/simulation/ARCHITECTURE.md)

