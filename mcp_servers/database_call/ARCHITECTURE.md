# Materials Database MCP Server Architecture

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│              Materials Database MCP Server                  │
│                    (FastMCP + SSE)                          │
│                  Port: 5002                                 │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Materials    │    │    OQMD      │    │     COD      │
│  Project     │    │   Rester     │    │   Search     │
│   API        │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  MP Database │    │OQMD Database │    │ COD Database │
│ 150,000+     │    │ 1,000,000+   │    │  500,000+    │
│ materials    │    │ materials    │    │ structures   │
└──────────────┘    └──────────────┘    └──────────────┘

        ┌───────────────────┬───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    AFLOW     │    │    Tavily    │    │   HTTP       │
│   Search     │    │   Search     │    │   Client     │
│              │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│AFLOW Database│    │  Web Search  │    │  Async I/O   │
│ 3,000,000+   │    │   Results    │    │   Timeout    │
│ materials    │    │              │    │   30s        │
└──────────────┘    └──────────────┘    └──────────────┘
```

## 核心组件

### 1. FastMCP Application

**初始化**:
```python
from fastmcp import FastMCP

app = FastMCP("materials-db")
```

**特点**:
- 基于 Server-Sent Events (SSE) 协议
- 支持异步工具调用
- 自动处理工具注册和路由

### 2. HTTP Client

**配置**:
```python
import httpx

http_client = httpx.AsyncClient(timeout=30.0)
```

**用途**:
- 异步 HTTP 请求
- 超时控制（30 秒）
- 连接池管理

### 3. 数据库客户端

#### Materials Project Client
```python
from mp_api.client import MPRester

with MPRester(MP_API_KEY) as mpr:
    docs = mpr.materials.summary.search(
        formula=formula,
        fields=fields_to_request
    )
```

**请求字段**:
```python
fields_to_request = [
    "structure",              # 晶体结构
    "volume",                 # 体积
    "material_id",            # 材料 ID
    "formula_pretty",         # 化学式
    "symmetry",               # 对称性
    "uncorrected_energy_per_atom",
    "energy_per_atom",
    "formation_energy_per_atom",
    "energy_above_hull",
    "is_stable",
    "band_gap",
    "efermi",
    "theoretical",
    "total_magnetization",
    "density",
    "density_atomic",
]
```

#### OQMD Client
```python
import qmpy_rester as qr

with qr.QMPYRester() as q:
    list_of_data = q.get_oqmd_phases(
        composition=composition,
        limit=3,
        verbose=False
    )
```

**查询参数**:
- `composition`: 化学组分
- `limit`: 结果数量限制
- `verbose`: 是否显示确认提示
- `element_set`: 元素集合（可选）
- `stability`: 稳定性阈值（可选）
- `natom`: 原子数限制（可选）

#### COD Client
```python
import requests

response = requests.get(
    "https://www.crystallography.net/cod/result",
    params={"formula": formula, "format": "json"}
)
```

**CIF 下载**:
```python
cif_url = f"https://www.crystallography.net/cod/{file_id}.cif"
cif_content = requests.get(cif_url).text
```

#### AFLOW Client
```python
from aflow import search, K

results = search(
    batch=K.auid,
    filter=K.species == formula
)
```

#### Tavily Client
```python
from langchain_tavily import TavilySearch

search_tool = TavilySearch(api_key=TAVILY_API_KEY)
results = search_tool.invoke(query)
```

## 工具实现

### 1. Materials Project Query Tool

**工具定义**:
```python
@app.tool
async def materials_project_query_tool(
    formula: str,
    num_return: int = 3
) -> str:
    """查询 Materials Project 数据库"""
```

**处理流程**:
```
1. 验证 API Key
2. 调用 MPRester.materials.summary.search()
3. 提取结构信息（晶格参数、原子位置）
4. 提取对称性信息（晶系、空间群）
5. 提取能量信息（形成能、稳定性）
6. 提取电子性质（带隙、费米能）
7. 提取物理性质（密度）
8. 格式化输出
9. 返回字符串结果
```

**数据转换**:
```python
# 晶格参数
lattice_params = (
    f"a={lattice.a:.3f}, b={lattice.b:.3f}, c={lattice.c:.3f}, "
    f"α={lattice.alpha:.2f}, β={lattice.beta:.2f}, γ={lattice.gamma:.2f}"
)

# 对称性信息
symmetry_info = (
    f"Crystal System: {doc.symmetry.crystal_system.value}, "
    f"Space Group: {doc.symmetry.symbol}"
)

# 格式化结果
result_str = f"""
  - Material ID: {doc.material_id}
    Source URL: https://next-gen.materialsproject.org/materials/{doc.material_id}
    Formula: {doc.formula_pretty}
    Symmetry: {symmetry_info}
    Structure:
      - Lattice Parameters: {lattice_params}
      - Sites: {sites}
      - Volume: {doc.volume:.4f} Å³
    Energy & Stability:
      - Is Stable: {'Yes' if doc.is_stable else 'No'}
      - Energy Above Hull: {doc.energy_above_hull:.4f} eV/atom
    ...
"""
```

### 2. OQMD Query Tool

**工具定义**:
```python
@app.tool
async def get_oqmd_phases(composition: str):
    """查询 OQMD 数据库"""
```

**处理流程**:
```
1. 调用 QMPYRester.get_oqmd_phases()
2. 遍历返回的数据
3. 提取简化信息：
   - material_id (entry_id)
   - icsd_id
   - name
   - composition
   - structure (space_group, unit_cell, sites, volume, stability)
4. 添加 source URL
5. 返回列表
```

**数据简化**:
```python
simplified = {
    "material_id": entry.get("entry_id", "N/A"),
    "icsd_id": entry.get("icsd_id", "N/A"),
    "name": entry.get("name", "N/A"),
    "composition": entry.get("composition", "N/A").strip(),
    "structure": {
        "space_group": entry.get("spacegroup", "N/A"),
        "unit_cell": entry.get("unit_cell", []),
        "sites": entry.get("sites", []),
        "volume": entry.get("volume", "N/A"),
        "stability": entry.get("stability", "N/A")
    },
    "source URL": f"https://oqmd.org/materials/entry/{entry.get('entry_id', 'N/A')}"
}
```

### 3. COD Search Tool

**工具定义**:
```python
@app.tool
async def search_cod_by_formula(formula: str):
    """查询 COD 数据库"""
```

**处理流程**:
```
1. 发送 GET 请求到 COD API
2. 解析 JSON 响应
3. 对每个结果：
   a. 下载 CIF 文件
   b. 提取简化信息
   c. 添加 source URL
4. 返回结果列表
```

**CIF 下载**:
```python
url = f"https://www.crystallography.net/cod/{entry.get('file', 'N/A')}.cif"
response = requests.get(url)
if response.status_code == 200:
    cif_content = response.text
else:
    cif_content = None
```

### 4. AFLOW Query Tool

**工具定义**:
```python
@app.tool
async def get_aflow_data(formula: str):
    """查询 AFLOW 数据库"""
```

**处理流程**:
```
1. 使用 aflow.search() 查询
2. 提取结果信息：
   - auid
   - compound
   - prototype
   - Pearson_symbol
   - space_group
   - lattice_parameters
3. 添加 source URL
4. 返回结果列表
```

## 数据流

### 成功查询流程

```
Database Agent
    │
    ▼
调用 materials_project_query_tool("LiFePO4")
    │
    ▼
MCP Server 接收请求
    │
    ▼
验证 API Key ✓
    │
    ▼
调用 MPRester.materials.summary.search()
    │
    ▼
Materials Project API
    │
    ▼
返回 MaterialSummary 对象列表
    │
    ▼
MCP Server 提取和格式化数据
    │
    ▼
返回格式化的字符串结果
    │
    ▼
Database Agent 接收结果
    │
    ▼
展示给用户
```

### 错误处理流程

```
Database Agent
    │
    ▼
调用 materials_project_query_tool("InvalidFormula")
    │
    ▼
MCP Server 接收请求
    │
    ▼
调用 MPRester.materials.summary.search()
    │
    ▼
Materials Project API 返回空结果
    │
    ▼
MCP Server 检测到空结果
    │
    ▼
返回 "No materials found for the formula 'InvalidFormula'"
    │
    ▼
Database Agent 接收错误消息
    │
    ▼
尝试下一个数据库
```

## 错误处理

### 1. API Key 缺失
```python
if not MP_API_KEY:
    return "Error: MP_API_KEY is not set in the environment variables."
```

### 2. API 调用异常
```python
try:
    docs = mpr.materials.summary.search(formula=formula)
except Exception as e:
    return f"An error occurred while querying the Materials Project API: {str(e)}"
```

### 3. 无结果
```python
if not docs:
    return f"No materials found for the formula '{formula}' in the Materials Project database."
```

### 4. HTTP 请求失败
```python
try:
    response = requests.get(base_url, params=params)
    response.raise_for_status()
except Exception as e:
    return f"Error: {e}"
```

## 性能优化

### 1. 异步处理
- 所有工具都是异步函数
- 使用 `async/await` 语法
- 支持并发查询

### 2. 结果限制
```python
# Materials Project: 最多返回 num_return 个结果
docs[:num_return]

# OQMD: 限制查询结果数量
kwargs = {"composition": composition, "limit": 3}
```

### 3. 超时控制
```python
http_client = httpx.AsyncClient(timeout=30.0)
```

### 4. 连接复用
- 使用 `httpx.AsyncClient` 维护连接池
- 避免重复建立连接

## 日志记录

使用 structlog 进行结构化日志：

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("Querying Materials Project", formula=formula)
logger.error("Query failed", error=str(e), formula=formula)
```

## 扩展性

### 添加新数据库

1. **安装客户端库**:
```bash
uv add new-database-client
```

2. **实现查询工具**:
```python
@app.tool
async def query_new_database(formula: str):
    """查询新数据库"""
    try:
        # 调用数据库 API
        results = new_db_client.search(formula)
        # 格式化结果
        return formatted_results
    except Exception as e:
        return f"Error: {str(e)}"
```

3. **更新文档**:
- 在 README.md 中添加工具说明
- 在 ARCHITECTURE.md 中添加实现细节

## 安全性

### 1. API Key 管理
```python
from dotenv import load_dotenv
import os

load_dotenv()
MP_API_KEY = os.getenv("MP_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
```

### 2. 输入验证
- 验证化学式格式
- 防止注入攻击

### 3. 错误信息
- 不暴露敏感信息（如 API Key）
- 提供友好的错误提示

## 相关文档

- [README.md](./README.md) - 使用指南
- [Database Agent Architecture](../../agents/database_agent/ARCHITECTURE.md) - Agent 架构

