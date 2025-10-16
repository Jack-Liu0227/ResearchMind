# Simulation Agent Architecture

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                   Simulation Agent                          │
│        (Google ADK Agent + LiteLLM + MCP Toolset)          │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ MCP Connection (SSE)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                Simulation MCP Server                        │
│                    (FastMCP)                                │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  CrystaLLM   │  │   AI4Kappa   │  │  MatterSim   │    │
│  │  Structure   │  │   Thermal    │  │   Energy     │    │
│  │  Generation  │  │ Conductivity │  │ Properties   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Simulation Agent (agents/simulation_agent/agent.py)

**职责**：
- 识别用户意图（生成结构、计算性质、设置计算）
- 协调 MCP 工具调用
- 提供进度更新
- 格式化输出结果

**关键代码**：
```python
root_agent = Agent(
    name="simulation_agent",
    model=LiteLlm(model=os.getenv('MODEL', 'gemini/gemini-2.5-flash')),
    instruction=SIMULATION_AGENT_INSTRUCTION,
    tools=[toolset]
)
```

**提示词模块化**：
```python
# prompts.py
SIMULATION_AGENT_INSTRUCTION = """
You are a computational materials scientist...

## CRITICAL BEHAVIOR RULES
### A. Crystal Structure Generation
### B. CIF File Calculations
### C. General Communication and Workflow
...
"""
```

### 2. MCP Toolset (mcp_servers/simulation/server.py)

**职责**：
- 提供计算工具
- 调用底层模型（CrystaLLM, AI4Kappa, MatterSim）
- 处理 CIF 文件
- 错误处理和日志记录

**工具分类**：

#### A. 晶体结构生成工具

```python
@app.tool
async def generate_crystal_structure(composition: str) -> Dict[str, Any]:
    """
    使用 CrystaLLM 生成晶体结构
    
    Args:
        composition: 化学组分，如 "GaN", "LiFePO4"
    
    Returns:
        {
            "status": "success",
            "composition": "GaN",
            "generation_id": "gen_12345",
            "cif_content": "data_GaN\n...",
            "generation_time": "2.5 minutes"
        }
    """
    # 调用 CrystaLLM 模型
    cif_content = crystallm.generate(composition)
    return result
```

**实现细节**：
- 调用 `mcp_servers/simulation/crystallm/` 模块
- 生成时间：2-5 分钟
- 返回标准 CIF 格式

#### B. CIF 处理工具

```python
@app.tool
async def extract_and_validate_cif(message_parts: List) -> Dict[str, Any]:
    """
    从文件上传中提取 CIF 内容
    
    Args:
        message_parts: 消息的 parts 列表（包含文件）
    
    Returns:
        {
            "status": "success",
            "cif_content": "data_...",
            "filename": "structure.cif",
            "validation": "valid"
        }
    """
    # 提取文件内容
    # 验证 CIF 格式
    return result
```

```python
@app.tool
async def validate_cif_content(cif_content: str) -> Dict[str, Any]:
    """验证 CIF 格式"""
    # 检查必需字段
    # 验证语法
    return validation_result
```

#### C. 热导率计算工具

```python
@app.tool
async def calculate_kappa_from_cif(
    cif_content: str,
    method: str = "kappa_p",
    temperature: float = 300.0
) -> Dict[str, Any]:
    """
    计算热导率
    
    Args:
        cif_content: CIF 文件内容
        method: "kappa_p" 或 "kappa_mtp"
        temperature: 温度（K）
    
    Returns:
        {
            "status": "success",
            "thermal_conductivity": 156.3,
            "unit": "W/m·K",
            "method": "kappa_p",
            "temperature": 300,
            "calculation_time": 45.2
        }
    """
    # 调用 AI4Kappa
    if method == "kappa_p":
        kappa = ai4kappa.kappa_p(cif_content, temperature)
    elif method == "kappa_mtp":
        kappa = ai4kappa.kappa_mtp(cif_content, temperature)
    return result
```

**实现细节**：
- 调用 `mcp_servers/simulation/kappa_lib/` 模块
- 支持两种方法：Kappa-P（快速）和 Kappa-MTP（精确）
- 默认温度：300 K

#### D. 能量属性计算工具

```python
@app.tool
async def calculate_energy_from_cif(cif_content: str) -> Dict[str, Any]:
    """
    使用 MatterSim 计算能量属性
    
    Args:
        cif_content: CIF 文件内容
    
    Returns:
        {
            "status": "success",
            "formation_energy": -2.45,
            "decomposition_energy": 0.12,
            "forces": [[...], ...],
            "stresses": [[...], ...],
            "unit": "eV/atom"
        }
    """
    # 调用 MatterSim 模型
    result = mattersim.predict(cif_content)
    return result
```

**实现细节**：
- 调用 `mcp_servers/simulation/models/mattersim/` 模块
- 返回多种能量属性
- 适用于稳定性分析

## 数据流

### 晶体结构生成流程

```
用户："生成 GaN 的晶体结构"
    │
    ▼
Simulation Agent 识别意图
    │
    ▼
提示用户："正在生成，需要几分钟..."
    │
    ▼
调用 generate_crystal_structure("GaN")
    │
    ▼
MCP Server 调用 CrystaLLM
    │
    ▼
CrystaLLM 生成结构（2-5 分钟）
    │
    ▼
返回 CIF 内容
    │
    ▼
Simulation Agent 展示结果
    │
    ▼
询问："您想计算热导率还是能量属性？"
```

### 热导率计算流程（文本粘贴）

```
用户：粘贴 CIF 内容 + "计算热导率"
    │
    ▼
Simulation Agent 检测 CIF 文本
    │
    ▼
识别关键字："data_", "_cell_length_a"
    │
    ▼
提示用户："正在计算热导率..."
    │
    ▼
调用 calculate_kappa_from_cif(cif_content, method="kappa_p")
    │
    ▼
MCP Server 调用 AI4Kappa
    │
    ▼
AI4Kappa 计算热导率（30-60 秒）
    │
    ▼
返回热导率值
    │
    ▼
Simulation Agent 展示结果
```

### 热导率计算流程（文件上传）

```
用户：上传 structure.cif + "计算热导率"
    │
    ▼
Simulation Agent 检测文件上传
    │
    ▼
调用 extract_and_validate_cif(message.parts)
    │
    ▼
MCP Server 提取 CIF 内容
    │
    ▼
返回 CIF 文本
    │
    ▼
Simulation Agent 提示："正在计算..."
    │
    ▼
调用 calculate_kappa_from_cif(cif_content)
    │
    ▼
返回热导率值
    │
    ▼
展示结果
```

## 关键行为规则

### 1. 立即行动原则
- 识别到化学组分 → 立即调用 `generate_crystal_structure`
- 识别到 CIF 内容 → 立即调用计算工具
- 不要只说不做

### 2. 进度更新原则
- 晶体结构生成：持续告知用户进度
- 计算过程：提示"正在计算..."
- 完成后：立即展示结果

### 3. 主动引导原则
- 生成结构后：询问是否需要计算性质
- 获取 CIF 后：如果意图不明确，询问一次后立即执行

### 4. 友好沟通原则
- ✅ "好的，我来为您..."
- ✅ "正在生成中..."
- ✅ "我看到您上传了..."
- ❌ "请注意..."
- ❌ "请确保..."

## 错误处理

### 1. CIF 格式错误
```python
if not is_valid_cif(cif_content):
    return {
        "status": "error",
        "error": "CIF 格式无效，请检查文件内容"
    }
```

### 2. 计算失败
```python
try:
    result = calculate_kappa(cif_content)
except Exception as e:
    return {
        "status": "error",
        "error": f"计算失败: {str(e)}"
    }
```

### 3. 文件提取失败
```python
if not cif_content:
    return {
        "status": "error",
        "error": "无法提取 CIF 内容，请确保上传了有效的 CIF 文件"
    }
```

## 性能优化

### 1. 异步处理
- 所有工具都是异步函数
- 支持并发计算

### 2. 缓存机制
- 缓存已生成的结构
- 缓存计算结果

### 3. 进度反馈
- 长时间计算提供进度更新
- 避免用户等待焦虑

## 扩展性

### 添加新计算工具

1. 在 MCP Server 中实现新工具：
```python
@app.tool
async def new_calculation_tool(cif_content: str) -> Dict[str, Any]:
    """新的计算工具"""
    # 实现计算逻辑
    return result
```

2. 在 Simulation Agent 的 instruction 中添加说明：
```python
SIMULATION_AGENT_INSTRUCTION = """
...
### D. New Calculation
- When user requests new calculation, call `new_calculation_tool`
...
"""
```

3. 更新文档

## 相关文档

- [README.md](./README.md) - 使用指南
- [MCP Server README](../../mcp_servers/simulation/README.md) - MCP 服务器文档
- [Database Agent](../database_agent/README.md) - 数据库查询代理

