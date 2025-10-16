# Database Agent Architecture

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Database Agent                          │
│  (Google ADK Agent + LiteLLM + MCP Toolset)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ MCP Connection
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Materials Database MCP Server                  │
│                  (FastMCP + SSE)                            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Materials    │  │    OQMD      │  │     COD      │    │
│  │  Project     │  │   Rester     │  │   Search     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │    AFLOW     │  │    Tavily    │                       │
│  │   Search     │  │   Search     │                       │
│  └──────────────┘  └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ AgentTool
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Simulation Agent                           │
│              (CrystaLLM Structure Generation)               │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Database Agent (agents/database_agent/agent.py)

**职责**：
- 协调多个数据库查询
- 验证化学式格式
- 决策查询策略
- 触发自动结构生成
- 格式化输出结果

**关键代码**：
```python
root_agent = Agent(
    name="database_agent",
    model=LiteLlm(model=os.getenv('MODEL', 'gemini/gemini-2.5-flash')),
    instruction=INSTRUCTION,
    tools=[toolset, AgentTool(agent=simulation_agent)]
)
```

**工作流程**：
1. 接收用户查询
2. 验证化学式（检查是否包含变量）
3. 按优先级调用数据库工具
4. 如果所有数据库都失败，调用 simulation_agent
5. 格式化并返回结果

### 2. MCP Toolset (mcp_servers/database_call/server.py)

**职责**：
- 提供数据库查询工具
- 处理 API 调用
- 数据格式转换
- 错误处理

**工具列表**：

#### Materials Project Tool
```python
@app.tool
async def materials_project_query_tool(formula: str, num_return: int = 3) -> str:
    """查询 Materials Project 数据库"""
    with MPRester(MP_API_KEY) as mpr:
        docs = mpr.materials.summary.search(
            formula=formula,
            fields=fields_to_request
        )
    return formatted_results
```

**返回字段**：
- `structure`: 晶体结构（晶格参数、原子位置）
- `symmetry`: 对称性信息（晶系、空间群）
- `energy_per_atom`: 能量
- `formation_energy_per_atom`: 形成能
- `energy_above_hull`: 相对于稳定相的能量
- `is_stable`: 是否稳定
- `band_gap`: 带隙
- `density`: 密度
- `total_magnetization`: 磁化强度

#### OQMD Tool
```python
@app.tool
async def get_oqmd_phases(composition: str):
    """查询 OQMD 数据库"""
    with qr.QMPYRester() as q:
        list_of_data = q.get_oqmd_phases(
            composition=composition,
            limit=3
        )
    return simplified_results
```

**返回字段**：
- `material_id`: OQMD entry ID
- `icsd_id`: ICSD ID
- `composition`: 标准化组分
- `structure`: 结构信息（空间群、晶胞、原子位置、体积）
- `stability`: 稳定性（hull distance）

#### COD Tool
```python
@app.tool
async def search_cod_by_formula(formula: str):
    """查询 COD 数据库"""
    response = requests.get(
        "https://www.crystallography.net/cod/result",
        params={"formula": formula, "format": "json"}
    )
    # 下载 CIF 文件
    cif_content = download_cif(entry['file'])
    return results_with_cif
```

**返回字段**：
- `file`: COD 文件 ID
- `formula`: 化学式
- `cellpars`: 晶胞参数
- `cif_content`: CIF 文件内容
- `source_url`: COD URL

#### AFLOW Tool
```python
@app.tool
async def get_aflow_data(formula: str):
    """查询 AFLOW 数据库"""
    results = search(
        batch=K.auid,
        filter=K.species == formula
    )
    return formatted_results
```

**返回字段**：
- `auid`: AFLOW 唯一 ID
- `compound`: 化合物名称
- `prototype`: 原型结构
- `Pearson_symbol`: Pearson 符号
- `space_group`: 空间群
- `lattice_parameters`: 晶格参数

#### Tavily Search Tool
```python
TavilySearch(api_key=TAVILY_API_KEY)
```

### 3. Simulation Agent Integration

**触发条件**：
- 所有数据库（MP, OQMD, COD, AFLOW）都未找到结构
- 网页搜索也未找到有效信息

**调用方式**：
```python
# 在 Database Agent 的 tools 中包含
AgentTool(agent=simulation_agent)
```

**工作流程**：
1. Database Agent 检测到所有数据库查询失败
2. 通知用户："未在数据库中找到 [化学式] 的晶体结构，正在自动生成..."
3. 调用 `simulation_agent` 工具，传入化学组分
4. Simulation Agent 使用 CrystaLLM 生成结构
5. 返回 CIF 文件内容
6. Database Agent 将 CIF 返回给用户

## 数据流

### 成功查询流程

```
用户输入 "查找 LiFePO4 的结构"
    │
    ▼
Database Agent 验证化学式 ✓
    │
    ▼
调用 materials_project_query_tool("LiFePO4")
    │
    ▼
MCP Server 查询 Materials Project API
    │
    ▼
返回结构数据（JSON）
    │
    ▼
Database Agent 格式化输出
    │
    ▼
用户收到结构信息
```

### 自动生成流程

```
用户输入 "查找 GaN 的结构"
    │
    ▼
Database Agent 验证化学式 ✓
    │
    ▼
调用 materials_project_query_tool("GaN") → 失败
    │
    ▼
调用 get_oqmd_phases("GaN") → 失败
    │
    ▼
调用 search_cod_by_formula("Ga N") → 失败
    │
    ▼
调用 get_aflow_data("GaN") → 失败
    │
    ▼
调用 TavilySearch("GaN crystal structure") → 失败
    │
    ▼
Database Agent 通知用户："正在自动生成..."
    │
    ▼
调用 simulation_agent(composition="GaN")
    │
    ▼
Simulation Agent 调用 CrystaLLM
    │
    ▼
返回生成的 CIF 结构
    │
    ▼
Database Agent 返回 CIF 给用户
    │
    ▼
提示用户可以用于后续计算
```

## 错误处理

### 1. 化学式验证错误
```python
if contains_variables(formula):
    return "化学式包含变量，无法查询数据库"
```

### 2. API 调用错误
```python
try:
    results = query_database(formula)
except Exception as e:
    return f"查询失败: {str(e)}"
```

### 3. 数据库无结果
```python
if not results:
    # 尝试下一个数据库
    # 如果所有数据库都失败，触发自动生成
```

## 性能优化

### 1. 查询优先级
- 优先使用 Materials Project（数据最全面）
- 其次 OQMD（开放数据库）
- 再次 COD（晶体学数据）
- 最后 AFLOW（自动化发现）

### 2. 结果限制
- 每个数据库最多返回 3 个结果
- 避免返回过多数据

### 3. 缓存机制
- MCP Server 可以实现查询缓存
- 减少重复 API 调用

## 安全性

### 1. API Key 管理
```python
MP_API_KEY = os.getenv("MP_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
```

### 2. 输入验证
- 验证化学式格式
- 防止注入攻击

### 3. 错误信息
- 不暴露敏感信息
- 提供友好的错误提示

## 扩展性

### 添加新数据库

1. 在 MCP Server 中添加新工具：
```python
@app.tool
async def query_new_database(formula: str):
    """查询新数据库"""
    # 实现查询逻辑
    return results
```

2. 在 Database Agent 的 instruction 中添加新数据库：
```python
instruction = """
...
- Try `query_new_database` if other databases fail
...
"""
```

### 添加新功能

1. 在 MCP Server 中实现新工具
2. 在 Database Agent 的 instruction 中说明何时使用
3. 更新文档

## 相关文档

- [README.md](./README.md) - 使用指南
- [MCP Server Architecture](../../mcp_servers/database_call/ARCHITECTURE.md) - MCP 服务器架构
- [Simulation Agent](../simulation_agent/ARCHITECTURE.md) - 结构生成架构

