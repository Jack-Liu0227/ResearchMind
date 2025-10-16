# ResearchMind - 材料科学研究协调系统

## 概述

ResearchMind 是一个基于 Google ADK 的多代理系统，专注于材料科学和计算化学研究。它通过协调三个专业子代理（文献研究、数据库检索、仿真计算）来完成从文献调研到材料性能计算的完整研究流程。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│              Research Coordinator Agent                     │
│           (主协调代理 - 智能分发请求)                        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Deep Research│    │   Database   │    │  Simulation  │
│    Agent     │    │    Agent     │    │    Agent     │
│              │    │              │    │              │
│ 文献研究助手  │    │ 数据库查询助手│    │ 仿真计算助手  │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Paper Search │    │ Materials DB │    │  Simulation  │
│  MCP Server  │    │  MCP Server  │    │  MCP Server  │
│              │    │              │    │              │
│ ArXiv+Tavily │    │ MP+OQMD+COD  │    │ CrystaLLM    │
│              │    │ +AFLOW       │    │ +AI4Kappa    │
│              │    │              │    │ +MatterSim   │
└──────────────┘    └──────────────┘    └──────────────┘
```

## 核心功能

### 1. 研究协调 (Research Coordinator)

**职责**：
- 智能分析用户请求
- 决策调用哪个子代理
- 协调多个子代理完成复杂任务
- 整合结果并提供综合分析

**工作流程**：
- **工作流程 A**：完整研究流程（文献 → 结构 → 计算）
- **工作流程 B**：快速计算流程（结构 → 计算）
- **工作流程 C**：仅文献调研

### 2. 深度文献研究 (Deep Research Agent)

**功能**：
- 多源搜索（ArXiv + Tavily）
- 论文分析和总结
- 生成研究报告
- 向量化存储和语义搜索

**详细文档**：[deep_research/README.md](./deep_research/README.md)

### 3. 数据库检索 (Database Agent)

**功能**：
- 查询多个材料数据库（MP, OQMD, COD, AFLOW）
- 获取晶体结构和材料属性
- **自动结构生成**：数据库查询失败时自动生成结构

**详细文档**：[database_agent/README.md](./database_agent/README.md)

### 4. 仿真计算 (Simulation Agent)

**功能**：
- 晶体结构生成（CrystaLLM）
- 热导率计算（AI4Kappa）
- 能量属性预测（MatterSim）

**详细文档**：[simulation_agent/README.md](./simulation_agent/README.md)

## 使用示例

### 示例 1：完整研究流程

```
用户："研究 GaN 的热导率"

Research Coordinator 响应：
1. 调用 deep_research_agent
   - 搜索 GaN 热导率相关文献
   - 生成文献综述报告

2. 调用 database_agent
   - 在数据库中查找 GaN 结构
   - 如果未找到，自动调用 simulation_agent 生成

3. 调用 simulation_agent
   - 使用 AI4Kappa 计算热导率
   - 使用 MatterSim 计算能量属性

4. 整合结果
   - 文献背景 + 结构信息 + 计算结果
   - 提供综合分析和建议
```

### 示例 2：快速计算流程

```
用户："计算 Si 的热导率"

Research Coordinator 响应：
1. 调用 database_agent
   - 在 Materials Project 中找到 Si 结构
   - 获取 CIF 文件

2. 调用 simulation_agent
   - 计算热导率：156.3 W/m·K
   - 计算能量属性

3. 返回结果
```

### 示例 3：仅文献调研

```
用户："综述大语言模型在材料设计中的应用"

Research Coordinator 响应：
1. 调用 deep_research_agent
   - 搜索相关论文
   - 分析研究趋势
   - 生成综述报告
```

### 示例 4：自动结构生成

```
用户："计算 GaN 的热导率"

Research Coordinator 响应：
1. 调用 database_agent
   - 在 MP, OQMD, COD, AFLOW 中查找 GaN
   - 所有数据库都未找到
   - 自动调用 simulation_agent 生成结构

2. simulation_agent 生成结构
   - 使用 CrystaLLM 生成 GaN 晶体结构
   - 返回 CIF 文件

3. 调用 simulation_agent 计算
   - 使用生成的 CIF 计算热导率
```

## 配置

### 环境变量

```bash
# .env 文件

# LLM 模型
MODEL_USE=gemini/gemini-2.5-flash

# Materials Project API Key
MP_API_KEY=your_mp_api_key

# Tavily Search API Key
TAVILY_API_KEY=your_tavily_key

# MCP 服务器 URL
PAPER_SEARCH_MCP_URL=http://localhost:50001/sse
DATABASE_MCP_URL=http://localhost:5002/sse
SIMULATION_MCP_URL=http://localhost:5003/sse
```

### 启动服务

#### 1. 启动 MCP 服务器

```bash
# 启动 Paper Search MCP Server
cd mcp_servers/paper_search
uv run python server.py

# 启动 Materials Database MCP Server
cd mcp_servers/database_call
uv run python server.py

# 启动 Simulation MCP Server
cd mcp_servers/simulation
uv run python server.py
```

#### 2. 启动 WebSocket 服务器

```bash
uv run python server.py
```

#### 3. 启动前端

```bash
cd ui
npm install
npm run dev
```

## 智能请求分发规则

Research Coordinator 根据用户请求的关键词自动决定调用哪个子代理：

### 文献研究类请求
**关键词**：文献、论文、综述、研究趋势、最新进展

**行动**：直接调用 `deep_research_agent`

### 材料结构查询类请求
**关键词**：晶体结构、CIF、材料数据库、结构信息

**行动**：调用 `database_agent`

**注意**：如果数据库查询失败，`database_agent` 会自动调用 `simulation_agent` 生成结构

### 性能计算类请求
**关键词**：热导率、能量、形成能、分解能、仿真

**行动**：
1. 先调用 `database_agent` 获取/生成结构
2. 再调用 `simulation_agent` 进行计算

### 综合研究类请求
**关键词**：研究、分析、评估（涉及多个方面）

**行动**：按照工作流程 A 依次调用三个代理

## 重要行为规则

### 1. 自动结构生成
- 当 `database_agent` 在所有数据库中都找不到材料结构时
- 自动调用 `simulation_agent` 的 `generate_crystal_structure` 工具
- 生成的结构可直接用于后续计算

### 2. 计算前必须有结构
- 任何性能计算（热导率、能量、声子谱）都需要 CIF 文件
- 优先从数据库获取，失败则自动生成

### 3. 保持用户知情
- 每个步骤都要告知用户当前进度
- 例如："正在数据库中查找结构..." → "未找到，正在生成结构..." → "结构已生成，开始计算..."

### 4. 错误处理
- 如果某个步骤失败，清晰说明原因
- 提供替代方案或建议

## 子代理详细文档

- [Deep Research Agent](./deep_research/README.md) - 文献研究助手
- [Database Agent](./database_agent/README.md) - 数据库查询助手
- [Simulation Agent](./simulation_agent/README.md) - 仿真计算助手

## MCP 服务器文档

- [Paper Search MCP Server](../mcp_servers/paper_search/README.md)
- [Materials Database MCP Server](../mcp_servers/database_call/README.md)
- [Simulation MCP Server](../mcp_servers/simulation/README.md)

## 架构文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 详细系统架构

## 更新日志

- **2025-10-07**: 
  - 添加自动晶体结构生成功能
  - 优化 Deep Research Agent 的表格生成功能
  - 更新所有文档

- **2025-10-06**: 初始版本

