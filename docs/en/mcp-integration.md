# MCP Integration Guide

Learn how to integrate Model Context Protocol (MCP) tools with ResearchMind agents for enhanced research capabilities.

## What is MCP?

Model Context Protocol (MCP) is a standardized protocol for connecting AI models with external tools and data sources. In ResearchMind, MCP enables agents to:

- 🔍 Search academic databases and literature
- 🗄️ Query materials property databases
- ⚛️ Run computational simulations
- 🧪 Design and optimize experiments
- 📊 Analyze and visualize data

## MCP Architecture Overview

### System Components
```
ResearchMind Agents
    ↓ (MCP Protocol)
MCP Servers
    ↓ (API Calls)
External Tools/Services
    ↓ (Data Return)
Research Results
```

### Current MCP Servers

#### 1. Literature Research Server
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

**Available Tools**:
- `search_arxiv` - ArXiv paper search
- `search_scholar` - Google Scholar search
- `search_web` - Web search
- `analyze_paper` - Paper analysis
- `generate_report` - Literature review generation

#### 2. Materials Database Server
```yaml
  materials:
    command: "python"
    args: ["mcp_servers/materials/server.py"]
    env:
      MATERIALS_PROJECT_API_KEY: "${MATERIALS_PROJECT_API_KEY}"
      OQMD_API_KEY: "${OQMD_API_KEY}"
    timeout: 60
```

**Available Tools**:
- `search_structure` - Structure search
- `generate_structure` - AI structure generation
- `predict_properties` - Property prediction
- `validate_structure` - Structure validation
- `visualize_structure` - Structure visualization

#### 3. Simulation Server
```yaml
  simulation:
    command: "python"
    args: ["mcp_servers/simulation/server.py"]
    env:
      MATTERSIM_LICENSE: "${MATTERSIM_LICENSE}"
      VASP_LICENSE: "${VASP_LICENSE}"
    timeout: 300
```

**Available Tools**:
- `setup_calculation` - Calculation setup
- `run_mattersim` - MatterSim calculations
- `analyze_results` - Result analysis
- `optimize_structure` - Structure optimization
- `calculate_properties` - Property calculations

#### 4. Experiment Design Server
```yaml
  experiment:
    command: "python"
    args: ["mcp_servers/experiment/server.py"]
    timeout: 30
```

**Available Tools**:
- `design_experiment` - Experiment design
- `optimize_parameters` - Parameter optimization
- `assess_risk` - Risk assessment
- `generate_protocol` - Protocol generation
- `estimate_cost` - Cost estimation

## Agent-MCP Integration

### Configuring Agent Toolsets
```python
# agents/literature_agent.py
from google.adk.agents import LlmAgent
from google.adk.mcp import MCPToolset, StdioConnectionParams

# Create MCP connection
literature_connection = StdioConnectionParams(
    command="python",
    args=["mcp_servers/literature/server.py"],
    env={"ARXIV_API_KEY": os.getenv("ARXIV_API_KEY")}
)

# Create toolset
literature_toolset = MCPToolset(literature_connection)

# Create agent
literature_agent = LlmAgent(
    name="literature_agent",
    model="gemini-2.0-flash",
    instruction="You are a literature research expert...",
    toolsets=[literature_toolset]
)
```

### Tool Filtering and Selection
```python
# Only expose specific tools to agent
filtered_toolset = MCPToolset(
    literature_connection,
    allowed_tools=["search_arxiv", "analyze_paper"]
)

# Or exclude certain tools
filtered_toolset = MCPToolset(
    literature_connection,
    denied_tools=["search_web"]
)
```

## Creating Custom MCP Servers

### Basic Server Structure
```python
# mcp_servers/custom/server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Create server instance
server = Server("custom-research-server")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="custom_search",
            description="Custom search tool",
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
    """Execute tool calls"""
    if name == "custom_search":
        query = arguments["query"]
        limit = arguments.get("limit", 10)
        
        # Implement search logic
        results = await perform_custom_search(query, limit)
        
        return [TextContent(
            type="text",
            text=f"Found {len(results)} results:\n" + 
                 "\n".join(results)
        )]
    
    raise ValueError(f"Unknown tool: {name}")

async def perform_custom_search(query: str, limit: int) -> list[str]:
    """Custom search implementation"""
    # Implement your search logic here
    return [f"Result {i}: {query} related content" for i in range(limit)]

if __name__ == "__main__":
    asyncio.run(stdio_server(server))
```

### Advanced Server Example
```python
# mcp_servers/advanced_materials/server.py
import asyncio
import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

server = Server("advanced-materials-server")

class MaterialsAPI:
    """Materials database API wrapper"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.materialsproject.org"
    
    async def search_materials(self, formula: str, properties: list) -> dict:
        """Search materials"""
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
        """Get structure information"""
        async with aiohttp.ClientSession() as session:
            headers = {"X-API-KEY": self.api_key}
            
            async with session.get(
                f"{self.base_url}/materials/{material_id}/structure",
                headers=headers
            ) as response:
                return await response.json()

# Initialize API
materials_api = MaterialsAPI(os.getenv("MATERIALS_PROJECT_API_KEY"))

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_advanced_materials",
            description="Advanced materials search",
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
            description="Visualize crystal structure",
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
        
        # Execute search
        results = await materials_api.search_materials(formula, properties)
        
        # Apply filters
        filtered_results = apply_filters(results, filters)
        
        # Format results
        formatted_results = format_search_results(filtered_results)
        
        return [TextContent(type="text", text=formatted_results)]
    
    elif name == "visualize_structure":
        material_id = arguments["material_id"]
        view_type = arguments.get("view_type", "3d")
        
        # Get structure data
        structure = await materials_api.get_structure(material_id)
        
        # Generate visualization
        image_data = generate_structure_visualization(structure, view_type)
        
        return [
            ImageContent(
                type="image",
                data=image_data,
                mimeType="image/png"
            ),
            TextContent(
                type="text",
                text=f"Structure visualization for {material_id} in {view_type} view"
            )
        ]
    
    raise ValueError(f"Unknown tool: {name}")

def apply_filters(results: dict, filters: dict) -> dict:
    """Apply search filters"""
    # Implement filtering logic
    return results

def format_search_results(results: dict) -> str:
    """Format search results"""
    # Implement formatting logic
    return "Formatted search results"

def generate_structure_visualization(structure: dict, view_type: str) -> bytes:
    """Generate structure visualization"""
    # Implement visualization logic
    return b"image data"
```

## Tool Development Best Practices

### 1. Error Handling
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
            text=f"Parameter error: {str(e)}"
        )]
    except TimeoutError:
        return [TextContent(
            type="text",
            text="Operation timed out, please try again"
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Unknown error: {str(e)}"
        )]
    
    raise ValueError(f"Unknown tool: {name}")
```

### 2. Input Validation
```python
def validate_arguments(arguments: dict, schema: dict) -> dict:
    """Validate input arguments"""
    import jsonschema
    
    try:
        jsonschema.validate(arguments, schema)
        return arguments
    except jsonschema.ValidationError as e:
        raise ValueError(f"Argument validation failed: {e.message}")
```

### 3. Caching and Performance
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
        
        # Try to get from cache
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # Execute actual search
        results = await self.search_materials(formula)
        
        # Cache results
        if self.redis:
            await self.redis.setex(
                cache_key, 
                3600,  # 1 hour expiry
                json.dumps(results)
            )
        
        return results
```

### 4. Logging and Monitoring
```python
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def log_tool_usage(func):
    """Log tool usage"""
    @wraps(func)
    async def wrapper(name: str, arguments: dict):
        start_time = time.time()
        logger.info(f"Calling tool: {name}, arguments: {arguments}")
        
        try:
            result = await func(name, arguments)
            duration = time.time() - start_time
            logger.info(f"Tool {name} executed successfully, duration: {duration:.2f}s")
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Tool {name} failed, duration: {duration:.2f}s, error: {str(e)}")
            raise
    
    return wrapper

@log_tool_usage
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # Tool implementation
    pass
```

## Testing MCP Servers

### Unit Testing
```python
# tests/test_materials_server.py
import pytest
import asyncio
from mcp_servers.materials.server import MaterialsAPI

@pytest.mark.asyncio
async def test_search_materials():
    """Test materials search functionality"""
    api = MaterialsAPI("test_api_key")
    
    # Mock API response
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value.__aenter__.return_value = mock_response
        
        results = await api.search_materials("Li2O", ["energy"])
        
        assert "data" in results
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_tool_call():
    """Test tool calling"""
    from mcp_servers.materials.server import call_tool
    
    arguments = {
        "formula": "Li2O",
        "properties": ["energy", "band_gap"]
    }
    
    results = await call_tool("search_advanced_materials", arguments)
    
    assert len(results) > 0
    assert results[0].type == "text"
```

### Integration Testing
```python
# tests/test_mcp_integration.py
import pytest
from google.adk.mcp import MCPToolset, StdioConnectionParams

@pytest.mark.asyncio
async def test_mcp_connection():
    """Test MCP connection"""
    connection = StdioConnectionParams(
        command="python",
        args=["mcp_servers/materials/server.py"]
    )
    
    toolset = MCPToolset(connection)
    
    # Test tool listing
    tools = await toolset.list_tools()
    assert len(tools) > 0
    
    # Test tool calling
    result = await toolset.call_tool(
        "search_structure",
        {"formula": "Li2O"}
    )
    assert result is not None
```

## Deployment and Monitoring

### Docker Deployment
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

### Health Checks
```python
# mcp_servers/materials/health.py
from mcp.server import Server

@server.list_resources()
async def list_resources():
    """Health check endpoint"""
    return [
        {
            "uri": "health://status",
            "name": "Server Status",
            "description": "MCP server health status"
        }
    ]

@server.read_resource()
async def read_resource(uri: str):
    """Read health status"""
    if uri == "health://status":
        # Check various service statuses
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

Through MCP integration, ResearchMind can connect to a wide variety of external tools and services, providing researchers with powerful and flexible research capabilities. Following best practices ensures tool reliability, performance, and maintainability.
