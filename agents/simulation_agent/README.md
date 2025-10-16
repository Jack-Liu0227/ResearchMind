# Simulation Agent (仿真计算助手)

## 📖 简介

Simulation Agent 是一个基于 Google ADK 构建的材料仿真计算助手。它通过 MCP (Model Context Protocol) 与 Simulation MCP Server 通信，提供从晶体结构生成、结构弛豫到声子谱计算、热导率计算、能量属性预测的完整仿真流程。

## ✨ 核心特性

### 🔬 晶体结构生成
- **CrystaLLM**：从化学式生成晶体结构（CIF 格式）
- **自动验证**：自动验证生成的结构是否合理

### 🔧 结构弛豫
- **MatterSim**：使用 ASE 优化器（BFGS, FIRE, LBFGS）优化晶体结构
- **能量优化**：最小化结构能量，获得稳定构型
- **结构变化**：展示弛豫前后的能量变化和结构变化

### 📊 声子谱计算
- **MatterSim**：计算声子色散和声子态密度
- **超胞设置**：支持自定义超胞矩阵（默认 4x4x4）
- **⚠️ 必须先弛豫**：计算声子谱前必须先调用 `relax_structure()`

### 🔥 热导率计算
- **AI4Kappa**：支持 Kappa-P（Slack 模型）和 Kappa-MTP（ML 预测）
- **温度设置**：支持自定义温度（默认 300K）
- **弛豫建议**：生成的结构建议先弛豫

### ⚡ 能量属性计算
- **MatterSim**：计算形成能、分解能、受力、应力
- **弛豫建议**：生成的结构建议先弛豫

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────────┐
│                  Simulation Agent                           │
│                  (Google ADK Agent)                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (SSE Transport)
┌─────────────────────────────────────────────────────────────┐
│              Simulation MCP Server                          │
│              (FastMCP Server - Port 5003)                   │
│                                                             │
│  8 个核心工具:                                               │
│  - 结构生成 (2个): generate_crystal_structure, ...         │
│  - 结构弛豫 (1个): relax_structure                          │
│  - 声子谱 (1个): calculate_phonon                           │
│  - 热导率 (1个): calculate_kappa_from_cif                   │
│  - 能量属性 (1个): calculate_energy_from_cif                │
│  - 其他 (2个): extract_and_validate_cif, ...               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              External Models                                │
│  - CrystaLLM (晶体结构生成)                                 │
│  - MatterSim (弛豫、声子谱、能量)                           │
│  - AI4Kappa (热导率计算)                                    │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 可用工具（8个）

### 1. 结构生成工具（2个）
- `generate_crystal_structure(composition)` - 从化学式生成晶体结构（CIF 格式）
- `extract_and_validate_cif(message_parts)` - 提取并验证用户提供的 CIF 文件

### 2. 结构弛豫工具（1个）
- `relax_structure(cif_content, optimizer="BFGS", max_steps=500, fmax=0.01)` - 结构弛豫

### 3. 声子谱工具（1个）
- `calculate_phonon(cif_content, supercell_matrix=[4,4,4])` - 计算声子谱（⚠️ 必须先弛豫）

### 4. 热导率工具（1个）
- `calculate_kappa_from_cif(cif_content, method="kappa_p", temperature=300.0)` - 计算热导率

### 5. 能量属性工具（1个）
- `calculate_energy_from_cif(cif_content)` - 计算形成能、分解能、受力、应力

## ⚠️ 核心规则（弛豫规则）

### 规则 1：计算声子谱前必须先弛豫
**适用范围**：所有结构（生成的结构 + 用户上传的结构）

**原因**：声子谱计算对结构精度要求极高，未弛豫的结构可能导致虚频或计算失败

**工作流程**：
```
1. generate_crystal_structure(composition) 或 extract_and_validate_cif(message_parts)
   → 获得初始 CIF
2. relax_structure(cif_content) → 获得弛豫后的 CIF（必须）
3. calculate_phonon(relaxed_cif_content) → 计算声子谱
```

### 规则 2：生成的结构计算能量/热导率前必须先弛豫
**适用范围**：仅生成的结构（`generate_crystal_structure` 生成的结构）

**原因**：生成的结构可能不是最稳定构型，弛豫后能量更准确

**工作流程**：
```
1. generate_crystal_structure(composition) → 获得初始 CIF
2. relax_structure(cif_content) → 获得弛豫后的 CIF（必须）
3. calculate_energy_from_cif(relaxed_cif_content) 或 calculate_kappa_from_cif(relaxed_cif_content)
```

### 规则 3：用户上传的结构计算能量/热导率不需要弛豫
**适用范围**：用户提供的 CIF 结构（`extract_and_validate_cif` 提取的结构）

**原因**：用户提供的结构通常已经是实验或计算优化后的结构

**工作流程**：
```
1. extract_and_validate_cif(message_parts) → 提取用户提供的 CIF
2. calculate_energy_from_cif(cif_content) 或 calculate_kappa_from_cif(cif_content)
   （不需要弛豫）
```

## 📋 标准工作流程

### 流程 1：生成结构 → 弛豫 → 计算声子谱
```
用户："生成 GaN 结构并计算声子谱"

步骤：
1. generate_crystal_structure(composition="GaN") → 获得初始 CIF
2. relax_structure(cif_content) → 获得弛豫后的 CIF（必须）
3. calculate_phonon(relaxed_cif_content) → 计算声子谱
4. 展示声子色散图和态密度
```

### 流程 2：生成结构 → 弛豫 → 计算热导率
```
用户："生成 GaN 结构并计算热导率"

步骤：
1. generate_crystal_structure(composition="GaN") → 获得初始 CIF
2. relax_structure(cif_content) → 获得弛豫后的 CIF（必须）
3. calculate_kappa_from_cif(relaxed_cif_content, method="kappa_p") → 计算热导率
4. 展示热导率值和计算方法
```

### 流程 3：生成结构 → 弛豫 → 计算能量属性
```
用户："生成 GaN 结构并计算能量属性"

步骤：
1. generate_crystal_structure(composition="GaN") → 获得初始 CIF
2. relax_structure(cif_content) → 获得弛豫后的 CIF（必须）
3. calculate_energy_from_cif(relaxed_cif_content) → 计算能量属性
4. 展示形成能、分解能、受力、应力
```

### 流程 4：用户提供 CIF → 计算能量/热导率（不需要弛豫）
```
用户："这是我的 GaN 结构（附 CIF 文件），计算热导率"

步骤：
1. extract_and_validate_cif(message_parts) → 提取用户提供的 CIF
2. calculate_kappa_from_cif(cif_content) → 计算热导率（不需要弛豫）
3. 展示热导率值
```

### 流程 5：用户提供 CIF → 弛豫 → 计算声子谱（必须弛豫）
```
用户："这是我的 GaN 结构（附 CIF 文件），计算声子谱"

步骤：
1. extract_and_validate_cif(message_parts) → 提取用户提供的 CIF
2. relax_structure(cif_content) → 获得弛豫后的 CIF（必须）
3. calculate_phonon(relaxed_cif_content) → 计算声子谱
4. 展示声子色散图和态密度
```

## 🎯 使用示例

### 示例 1：生成结构并计算声子谱
```
用户："生成 GaN 结构并计算声子谱"

步骤：
1. generate_crystal_structure(composition="GaN")
   → 获得初始 CIF
2. relax_structure(cif_content, optimizer="BFGS", max_steps=500, fmax=0.01)
   → 获得弛豫后的 CIF
   → 展示弛豫前后的能量变化和结构变化
3. calculate_phonon(relaxed_cif_content, supercell_matrix=[4,4,4])
   → 计算声子谱
   → 展示声子色散图和态密度
```

### 示例 2：生成结构并计算热导率
```
用户："生成 GaN 结构并计算热导率"

步骤：
1. generate_crystal_structure(composition="GaN")
2. relax_structure(cif_content)
3. calculate_kappa_from_cif(relaxed_cif_content, method="kappa_p", temperature=300.0)
   → 展示热导率值（W/m·K）
```

### 示例 3：用户提供 CIF 并计算能量
```
用户："这是我的 GaN 结构（附 CIF 文件），计算能量属性"

步骤：
1. extract_and_validate_cif(message_parts)
   → 提取用户提供的 CIF
2. calculate_energy_from_cif(cif_content)
   → 展示形成能、分解能、受力、应力
```

## 🚀 快速开始

### 前置要求
- Python 3.11+
- UV (Python 包管理工具)
- Google API Key (用于 Gemini 2.0 Flash)

### 安装依赖
```bash
uv sync
```

### 配置环境变量
创建 `.env` 文件：
```bash
# Google API Key
GOOGLE_API_KEY=your_google_api_key_here
```

### 启动 Simulation MCP Server
```bash
uv run python mcp_servers/simulation/server.py
```

### 启动 Simulation Agent
```bash
uv run python agents/simulation_agent/agent.py
```

## 📁 项目结构

```
agents/simulation_agent/
├── agent.py                # Agent 实现
├── prompts.py              # 提示词
├── README.md               # 文档（本文件）
└── ARCHITECTURE.md         # 架构说明
```

## 🛠️ 技术栈

- **Google ADK**: AI Agent 开发框架
- **Gemini 2.0 Flash**: Google 最新的多模态大语言模型
- **FastMCP**: MCP Server 开发框架
- **SSE (Server-Sent Events)**: Agent 与 Server 通信协议
- **CrystaLLM**: 晶体结构生成模型
- **MatterSim**: 能量属性和声子谱计算模型
- **AI4Kappa**: 热导率计算模型

## 📖 相关文档

- **Simulation MCP Server**: [mcp_servers/simulation/README.md](../../mcp_servers/simulation/README.md)
- **项目主文档**: [README.md](../../README.md)
- **项目简介**: [INTRO.md](../../INTRO.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

