# Simulation MCP Server Architecture

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                Simulation MCP Server                        │
│                    (FastMCP + SSE)                          │
│                  Port: 5003                                 │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  CrystaLLM   │    │   AI4Kappa   │    │  MatterSim   │
│  Structure   │    │   Thermal    │    │   Energy     │
│  Generation  │    │ Conductivity │    │ Properties   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ LLM-based    │    │   Kappa-P    │    │  Formation   │
│ Generation   │    │   Kappa-MTP  │    │  Energy      │
│ 2-5 min      │    │   30-60 sec  │    │  Forces      │
└──────────────┘    └──────────────┘    └──────────────┘

```

## 核心组件

### 1. FastMCP Application

**初始化**:
```python
from fastmcp import FastMCP

app = FastMCP("simulation")
```

**特点**:
- 基于 Server-Sent Events (SSE) 协议
- 支持异步工具调用
- 自动处理工具注册和路由

### 2. 模型模块

#### CrystaLLM 模块
**位置**: `mcp_servers/simulation/crystallm/`

**功能**: 从化学组分生成晶体结构

**接口**:
```python
def generate(composition: str) -> str:
    """
    生成晶体结构
    
    Args:
        composition: 化学组分，如 "GaN"
    
    Returns:
        CIF 格式的晶体结构
    """
```

**特点**:
- 基于大语言模型
- 生成时间：2-5 分钟
- 输出标准 CIF 格式

#### AI4Kappa 模块
**位置**: `mcp_servers/simulation/kappa_lib/`

**功能**: 计算热导率

**接口**:
```python
def kappa_p(cif_content: str, temperature: float) -> float:
    """Kappa-P 方法计算热导率"""

def kappa_mtp(cif_content: str, temperature: float) -> float:
    """Kappa-MTP 方法计算热导率"""
```

**方法对比**:
| 方法 | 速度 | 精度 | 适用场景 |
|------|------|------|----------|
| Kappa-P | 快（30-60秒） | 中等 | 快速筛选 |
| Kappa-MTP | 慢（2-5分钟） | 高 | 精确计算 |

#### MatterSim 模块
**位置**: `mcp_servers/simulation/models/mattersim/`

**功能**: 预测能量属性

**接口**:
```python
def predict(cif_content: str) -> Dict[str, Any]:
    """
    预测能量属性
    
    Returns:
        {
            "formation_energy": float,
            "decomposition_energy": float,
            "forces": List[List[float]],
            "stresses": List[List[float]]
        }
    """
```

**特点**:
- 基于机器学习模型
- 快速预测（几秒钟）
- 多种能量属性

## 工具实现

### 1. 晶体结构生成工具

**工具定义**:
```python
@app.tool
async def generate_crystal_structure(composition: str) -> Dict[str, Any]:
    """使用 CrystaLLM 生成晶体结构"""
```

**处理流程**:
```
1. 接收化学组分
2. 调用 CrystaLLM 模块
3. 生成晶体结构（2-5 分钟）
4. 验证 CIF 格式
5. 生成唯一 ID
6. 记录生成信息
7. 返回结果
```

**实现细节**:
```python
async def generate_crystal_structure(composition: str) -> Dict[str, Any]:
    try:
        # 生成唯一 ID
        generation_id = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 调用 CrystaLLM
        start_time = time.time()
        cif_content = crystallm.generate(composition)
        generation_time = time.time() - start_time
        
        # 验证 CIF
        if not is_valid_cif(cif_content):
            raise ValueError("Generated CIF is invalid")
        
        return {
            "status": "success",
            "composition": composition,
            "generation_id": generation_id,
            "model_used": "CrystaLLM-v1.0",
            "cif_content": cif_content,
            "generation_time": f"{generation_time/60:.1f} minutes",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

### 2. CIF 处理工具

#### 提取和验证 CIF
**工具定义**:
```python
@app.tool
async def extract_and_validate_cif(message_parts: List) -> Dict[str, Any]:
    """从文件上传中提取 CIF 内容"""
```

**处理流程**:
```
1. 遍历 message_parts
2. 查找文件类型的 part
3. 提取文件内容
4. 解码为文本
5. 验证 CIF 格式
6. 返回 CIF 内容
```

**实现细节**:
```python
async def extract_and_validate_cif(message_parts: List) -> Dict[str, Any]:
    for part in message_parts:
        if hasattr(part, 'inline_data'):
            # 提取文件内容
            file_data = part.inline_data.data
            mime_type = part.inline_data.mime_type
            
            # 解码
            if mime_type == "text/plain" or "cif" in mime_type:
                cif_content = file_data.decode('utf-8')
                
                # 验证
                validation = validate_cif_content(cif_content)
                
                return {
                    "status": "success",
                    "cif_content": cif_content,
                    "filename": getattr(part, 'filename', 'unknown.cif'),
                    "validation": validation
                }
    
    return {
        "status": "error",
        "error": "No CIF file found in message"
    }
```

#### 验证 CIF 内容
**工具定义**:
```python
@app.tool
async def validate_cif_content(cif_content: str) -> Dict[str, Any]:
    """验证 CIF 格式"""
```

**验证规则**:
```python
def validate_cif_content(cif_content: str) -> Dict[str, Any]:
    errors = []
    warnings = []
    
    # 检查必需字段
    required_fields = [
        "_cell_length_a",
        "_cell_length_b",
        "_cell_length_c",
        "_atom_site_label"
    ]
    
    for field in required_fields:
        if field not in cif_content:
            errors.append(f"Missing required field: {field}")
    
    # 检查数据块
    if not cif_content.startswith("data_"):
        warnings.append("CIF should start with 'data_'")
    
    if errors:
        return {"status": "invalid", "errors": errors, "warnings": warnings}
    else:
        return {"status": "valid", "errors": [], "warnings": warnings}
```

### 3. 热导率计算工具

**工具定义**:
```python
@app.tool
async def calculate_kappa_from_cif(
    cif_content: str,
    method: str = "kappa_p",
    temperature: float = 300.0
) -> Dict[str, Any]:
    """计算热导率"""
```

**处理流程**:
```
1. 验证 CIF 内容
2. 选择计算方法
3. 调用 AI4Kappa 模块
4. 记录计算时间
5. 提取组分信息
6. 返回结果
```

**实现细节**:
```python
async def calculate_kappa_from_cif(
    cif_content: str,
    method: str = "kappa_p",
    temperature: float = 300.0
) -> Dict[str, Any]:
    try:
        # 验证 CIF
        validation = validate_cif_content(cif_content)
        if validation["status"] != "valid":
            raise ValueError(f"Invalid CIF: {validation['errors']}")
        
        # 计算热导率
        start_time = time.time()
        if method == "kappa_p":
            kappa = ai4kappa.kappa_p(cif_content, temperature)
        elif method == "kappa_mtp":
            kappa = ai4kappa.kappa_mtp(cif_content, temperature)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        calculation_time = time.time() - start_time
        
        # 提取组分
        composition = extract_composition_from_cif(cif_content)
        
        return {
            "status": "success",
            "thermal_conductivity": kappa,
            "unit": "W/m·K",
            "method": method,
            "temperature": temperature,
            "calculation_time": calculation_time,
            "composition": composition,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

### 4. 能量属性计算工具

**工具定义**:
```python
@app.tool
async def calculate_energy_from_cif(cif_content: str) -> Dict[str, Any]:
    """使用 MatterSim 计算能量属性"""
```

**处理流程**:
```
1. 验证 CIF 内容
2. 调用 MatterSim 模块
3. 提取多种能量属性
4. 返回结果
```

**实现细节**:
```python
async def calculate_energy_from_cif(cif_content: str) -> Dict[str, Any]:
    try:
        # 验证 CIF
        validation = validate_cif_content(cif_content)
        if validation["status"] != "valid":
            raise ValueError(f"Invalid CIF: {validation['errors']}")
        
        # 调用 MatterSim
        result = mattersim.predict(cif_content)
        
        return {
            "status": "success",
            "formation_energy": result["formation_energy"],
            "decomposition_energy": result["decomposition_energy"],
            "forces": result["forces"],
            "stresses": result["stresses"],
            "unit": "eV/atom",
            "model": "MatterSim",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

## 数据流

### 晶体结构生成流程

```
Simulation Agent
    │
    ▼
调用 generate_crystal_structure("GaN")
    │
    ▼
MCP Server 接收请求
    │
    ▼
调用 CrystaLLM 模块
    │
    ▼
CrystaLLM 生成结构（2-5 分钟）
    │
    ▼
验证 CIF 格式 ✓
    │
    ▼
生成唯一 ID
    │
    ▼
返回结果（包含 CIF 内容）
    │
    ▼
Simulation Agent 接收结果
    │
    ▼
展示给用户
```

### 热导率计算流程

```
Simulation Agent
    │
    ▼
调用 calculate_kappa_from_cif(cif_content, "kappa_p")
    │
    ▼
MCP Server 接收请求
    │
    ▼
验证 CIF 内容 ✓
    │
    ▼
调用 AI4Kappa.kappa_p()
    │
    ▼
AI4Kappa 计算热导率（30-60 秒）
    │
    ▼
返回热导率值
    │
    ▼
MCP Server 格式化结果
    │
    ▼
Simulation Agent 接收结果
    │
    ▼
展示给用户
```

## 错误处理

### 1. CIF 格式错误
```python
if validation["status"] != "valid":
    return {
        "status": "error",
        "error": f"Invalid CIF: {validation['errors']}"
    }
```

### 2. 计算失败
```python
try:
    kappa = ai4kappa.kappa_p(cif_content, temperature)
except Exception as e:
    return {
        "status": "error",
        "error": f"Calculation failed: {str(e)}"
    }
```

### 3. 文件提取失败
```python
if not cif_content:
    return {
        "status": "error",
        "error": "No CIF file found in message"
    }
```

## 性能优化

### 1. 异步处理
- 所有工具都是异步函数
- 支持并发计算

### 2. 进度反馈
- 长时间计算提供进度更新
- 避免超时

### 3. 结果缓存
- 缓存已生成的结构
- 缓存计算结果

## 日志记录

使用 structlog 进行结构化日志：

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("Generating crystal structure", composition=composition)
logger.info("Calculating thermal conductivity", method=method)
logger.error("Calculation failed", error=str(e))
```

## 扩展性

### 添加新计算工具

1. **实现计算模块**:
```python
# mcp_servers/simulation/modules/new_tool.py
def new_calculation(cif_content: str) -> Dict[str, Any]:
    """新的计算功能"""
    # 实现计算逻辑
    return result
```

2. **注册 MCP 工具**:
```python
@app.tool
async def new_calculation_tool(cif_content: str) -> Dict[str, Any]:
    """新的计算工具"""
    try:
        result = new_calculation(cif_content)
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

3. **更新文档**

## 相关文档

- [README.md](./README.md) - 使用指南
- [Simulation Agent Architecture](../../agents/simulation_agent/ARCHITECTURE.md) - Agent 架构

