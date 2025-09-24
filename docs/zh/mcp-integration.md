# MCP集成指南

学习如何将Model Context Protocol (MCP) 工具与ResearchMind智能体集成，以增强研究能力。

> 🇺🇸 **English Users**: [Click here for English version](../mcp-integration.md) | **英文用户**: [点击这里查看英文版本](../mcp-integration.md)

## 什么是MCP？

Model Context Protocol (MCP) 是一个标准化协议，用于连接AI模型与外部工具和数据源。在ResearchMind中，MCP使智能体能够：

- 🔍 搜索学术数据库和文献
- 🗄️ 查询材料性质数据库
- ⚛️ 运行计算仿真
- 🧪 设计和优化实验
- 📊 分析和可视化数据

## MCP架构概览

### 系统组件
```
ResearchMind智能体
    ↓ (MCP协议)
MCP服务器
    ↓ (API调用)
外部工具/服务
    ↓ (数据返回)
研究结果
```

### 当前MCP服务器

#### 1. 文献研究服务器
```yaml
# config/mcp_config.yaml
mcp_servers:
  literature:
    command: "python"
    args: ["mcp_servers/literature/server.py"]
    env:
      ARXIV_API_KEY: "${ARXIV_API_KEY}"
      SCHOLAR_API_KEY: "${SCHOLAR_API_KEY}"
    timeout: 30
```

**可用工具**:
- `search_arxiv` - ArXiv论文搜索
- `search_scholar` - Google Scholar搜索
- `search_web` - 网络搜索
- `analyze_paper` - 论文分析
- `generate_report` - 生成文献综述

#### 2. 材料数据库服务器
```yaml
  materials:
    command: "python"
    args: ["mcp_servers/materials/server.py"]
    env:
      MATERIALS_PROJECT_API_KEY: "${MATERIALS_PROJECT_API_KEY}"
      OQMD_API_KEY: "${OQMD_API_KEY}"
    timeout: 60
```

**可用工具**:
- `search_structure` - 结构搜索
- `generate_structure` - AI结构生成
- `predict_properties` - 性质预测
- `validate_structure` - 结构验证
- `visualize_structure` - 结构可视化

#### 3. 仿真计算服务器
```yaml
  simulation:
    command: "python"
    args: ["mcp_servers/simulation/server.py"]
    env:
      MATTERSIM_LICENSE: "${MATTERSIM_LICENSE}"
      VASP_LICENSE: "${VASP_LICENSE}"
    timeout: 300
```

**可用工具**:
- `setup_calculation` - 计算设置
- `run_mattersim` - MatterSim计算
- `analyze_results` - 结果分析
- `optimize_structure` - 结构优化
- `calculate_properties` - 性质计算

#### 4. 实验设计服务器
```yaml
  experiment:
    command: "python"
    args: ["mcp_servers/experiment/server.py"]
    timeout: 30
```

**可用工具**:
- `design_experiment` - 实验设计
- `optimize_parameters` - 参数优化
- `assess_risk` - 风险评估
- `generate_protocol` - 协议生成
- `estimate_cost` - 成本估算

## 智能体与MCP集成

### 配置智能体工具集
```python
# agents/literature_agent.py
from google.adk.agents import LlmAgent
from google.adk.mcp import MCPToolset, StdioConnectionParams

# 创建MCP连接
literature_connection = StdioConnectionParams(
    command="python",
    args=["mcp_servers/literature/server.py"],
    env={"ARXIV_API_KEY": os.getenv("ARXIV_API_KEY")}
)

# 创建工具集
literature_toolset = MCPToolset(literature_connection)

# 创建智能体
literature_agent = LlmAgent(
    name="literature_agent",
    model="gemini-2.0-flash",
    instruction="您是文献研究专家...",
    toolsets=[literature_toolset]
)
```

### 工具过滤和选择
```python
# 只暴露特定工具给智能体
filtered_toolset = MCPToolset(
    literature_connection,
    allowed_tools=["search_arxiv", "analyze_paper"]
)

# 或者排除某些工具
filtered_toolset = MCPToolset(
    literature_connection,
    denied_tools=["search_web"]
)
```

## 创建自定义MCP服务器

### 基础服务器结构
```python
# mcp_servers/custom/server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 创建服务器实例
server = Server("custom-research-server")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="custom_search",
            description="自定义搜索工具",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """执行工具调用"""
    if name == "custom_search":
        query = arguments["query"]
        limit = arguments.get("limit", 10)
        
        # 实现搜索逻辑
        results = await perform_custom_search(query, limit)
        
        return [TextContent(
            type="text",
            text=f"找到 {len(results)} 个结果:\n" + 
                 "\n".join(results)
        )]
    
    raise ValueError(f"未知工具: {name}")

async def perform_custom_search(query: str, limit: int) -> list[str]:
    """自定义搜索实现"""
    # 这里实现您的搜索逻辑
    return [f"结果 {i}: {query} 相关内容" for i in range(limit)]

if __name__ == "__main__":
    asyncio.run(stdio_server(server))
```

### 高级服务器示例
```python
# mcp_servers/advanced_materials/server.py
import asyncio
import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

server = Server("advanced-materials-server")

class MaterialsAPI:
    """材料数据库API包装器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.materialsproject.org"
    
    async def search_materials(self, formula: str, properties: list) -> dict:
        """搜索材料"""
        async with aiohttp.ClientSession() as session:
            headers = {"X-API-KEY": self.api_key}
            params = {
                "formula": formula,
                "properties": ",".join(properties)
            }
            
            async with session.get(
                f"{self.base_url}/materials",
                headers=headers,
                params=params
            ) as response:
                return await response.json()
    
    async def get_structure(self, material_id: str) -> dict:
        """获取结构信息"""
        async with aiohttp.ClientSession() as session:
            headers = {"X-API-KEY": self.api_key}
            
            async with session.get(
                f"{self.base_url}/materials/{material_id}/structure",
                headers=headers
            ) as response:
                return await response.json()

# 初始化API
materials_api = MaterialsAPI(os.getenv("MATERIALS_PROJECT_API_KEY"))

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_advanced_materials",
            description="高级材料搜索",
            inputSchema={
                "type": "object",
                "properties": {
                    "formula": {"type": "string"},
                    "properties": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["energy", "band_gap"]
                    },
                    "filters": {
                        "type": "object",
                        "properties": {
                            "energy_above_hull": {"type": "number"},
                            "band_gap_min": {"type": "number"},
                            "band_gap_max": {"type": "number"}
                        }
                    }
                },
                "required": ["formula"]
            }
        ),
        Tool(
            name="visualize_structure",
            description="可视化晶体结构",
            inputSchema={
                "type": "object",
                "properties": {
                    "material_id": {"type": "string"},
                    "view_type": {
                        "type": "string",
                        "enum": ["3d", "2d", "unit_cell"],
                        "default": "3d"
                    }
                },
                "required": ["material_id"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:
    if name == "search_advanced_materials":
        formula = arguments["formula"]
        properties = arguments.get("properties", ["energy", "band_gap"])
        filters = arguments.get("filters", {})
        
        # 执行搜索
        results = await materials_api.search_materials(formula, properties)
        
        # 应用过滤器
        filtered_results = apply_filters(results, filters)
        
        # 格式化结果
        formatted_results = format_search_results(filtered_results)
        
        return [TextContent(type="text", text=formatted_results)]
    
    elif name == "visualize_structure":
        material_id = arguments["material_id"]
        view_type = arguments.get("view_type", "3d")
        
        # 获取结构数据
        structure = await materials_api.get_structure(material_id)
        
        # 生成可视化
        image_data = generate_structure_visualization(structure, view_type)
        
        return [
            ImageContent(
                type="image",
                data=image_data,
                mimeType="image/png"
            ),
            TextContent(
                type="text",
                text=f"材料 {material_id} 的 {view_type} 结构图"
            )
        ]
    
    raise ValueError(f"未知工具: {name}")

def apply_filters(results: dict, filters: dict) -> dict:
    """应用搜索过滤器"""
    # 实现过滤逻辑
    return results

def format_search_results(results: dict) -> str:
    """格式化搜索结果"""
    # 实现格式化逻辑
    return "格式化的搜索结果"

def generate_structure_visualization(structure: dict, view_type: str) -> bytes:
    """生成结构可视化"""
    # 实现可视化逻辑
    return b"图像数据"
```

## 工具开发最佳实践

### 1. 错误处理
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "risky_operation":
            result = await perform_risky_operation(arguments)
            return [TextContent(type="text", text=result)]
    
    except ValueError as e:
        return [TextContent(
            type="text",
            text=f"参数错误: {str(e)}"
        )]
    except TimeoutError:
        return [TextContent(
            type="text",
            text="操作超时，请稍后重试"
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"未知错误: {str(e)}"
        )]
    
    raise ValueError(f"未知工具: {name}")
```

### 2. 输入验证
```python
def validate_arguments(arguments: dict, schema: dict) -> dict:
    """验证输入参数"""
    import jsonschema
    
    try:
        jsonschema.validate(arguments, schema)
        return arguments
    except jsonschema.ValidationError as e:
        raise ValueError(f"参数验证失败: {e.message}")
```

### 3. 缓存和性能
```python
import asyncio
from functools import lru_cache
import aioredis

class CachedMaterialsAPI:
    def __init__(self):
        self.redis = None
    
    async def init_redis(self):
        self.redis = await aioredis.from_url("redis://localhost")
    
    async def search_materials_cached(self, formula: str) -> dict:
        cache_key = f"materials:{formula}"
        
        # 尝试从缓存获取
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # 执行实际搜索
        results = await self.search_materials(formula)
        
        # 缓存结果
        if self.redis:
            await self.redis.setex(
                cache_key, 
                3600,  # 1小时过期
                json.dumps(results)
            )
        
        return results
```

### 4. 日志和监控
```python
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def log_tool_usage(func):
    """记录工具使用情况"""
    @wraps(func)
    async def wrapper(name: str, arguments: dict):
        start_time = time.time()
        logger.info(f"调用工具: {name}, 参数: {arguments}")
        
        try:
            result = await func(name, arguments)
            duration = time.time() - start_time
            logger.info(f"工具 {name} 执行成功, 耗时: {duration:.2f}s")
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"工具 {name} 执行失败, 耗时: {duration:.2f}s, 错误: {str(e)}")
            raise
    
    return wrapper

@log_tool_usage
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # 工具实现
    pass
```

## 测试MCP服务器

### 单元测试
```python
# tests/test_materials_server.py
import pytest
import asyncio
from mcp_servers.materials.server import MaterialsAPI

@pytest.mark.asyncio
async def test_search_materials():
    """测试材料搜索功能"""
    api = MaterialsAPI("test_api_key")
    
    # 模拟API响应
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value.__aenter__.return_value = mock_response
        
        results = await api.search_materials("Li2O", ["energy"])
        
        assert "data" in results
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_tool_call():
    """测试工具调用"""
    from mcp_servers.materials.server import call_tool
    
    arguments = {
        "formula": "Li2O",
        "properties": ["energy", "band_gap"]
    }
    
    results = await call_tool("search_advanced_materials", arguments)
    
    assert len(results) > 0
    assert results[0].type == "text"
```

### 集成测试
```python
# tests/test_mcp_integration.py
import pytest
from google.adk.mcp import MCPToolset, StdioConnectionParams

@pytest.mark.asyncio
async def test_mcp_connection():
    """测试MCP连接"""
    connection = StdioConnectionParams(
        command="python",
        args=["mcp_servers/materials/server.py"]
    )
    
    toolset = MCPToolset(connection)
    
    # 测试工具列表
    tools = await toolset.list_tools()
    assert len(tools) > 0
    
    # 测试工具调用
    result = await toolset.call_tool(
        "search_structure",
        {"formula": "Li2O"}
    )
    assert result is not None
```

## 部署和监控

### Docker部署
```dockerfile
# mcp_servers/materials/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["python", "server.py", "--port", "8080"]
```

### 健康检查
```python
# mcp_servers/materials/health.py
from mcp.server import Server

@server.list_resources()
async def list_resources():
    """健康检查端点"""
    return [
        {
            "uri": "health://status",
            "name": "服务器状态",
            "description": "MCP服务器健康状态"
        }
    ]

@server.read_resource()
async def read_resource(uri: str):
    """读取健康状态"""
    if uri == "health://status":
        # 检查各种服务状态
        status = await check_service_health()
        return {
            "contents": [
                {
                    "type": "text",
                    "text": json.dumps(status, indent=2)
                }
            ]
        }
```

---

通过MCP集成，ResearchMind能够连接到各种外部工具和服务，为研究人员提供强大而灵活的研究能力。遵循最佳实践可以确保工具的可靠性、性能和可维护性。
