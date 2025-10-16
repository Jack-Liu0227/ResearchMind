# Simulation MCP Server

## 📖 简介

Simulation MCP Server 是一个基于 FastMCP 构建的材料仿真计算服务器。它提供 8 个核心工具，支持晶体结构生成、结构弛豫、声子谱计算、热导率计算和能量属性预测。

## ✨ 核心特性

### 🔬 晶体结构生成
- **CrystaLLM**：从化学式生成晶体结构（CIF 格式）
- **自动验证**：自动验证生成的结构是否合理

### 🔧 结构弛豫
- **MatterSim**：使用 ASE 优化器（BFGS, FIRE, LBFGS）优化晶体结构
- **能量优化**：最小化结构能量，获得稳定构型

### 📊 声子谱计算
- **MatterSim**：计算声子色散和声子态密度
- **⚠️ 必须先弛豫**：计算声子谱前必须先调用 `relax_structure()`

### 🔥 热导率计算
- **AI4Kappa**：支持 Kappa-P（Slack 模型）和 Kappa-MTP（ML 预测）

### ⚡ 能量属性计算
- **MatterSim**：计算形成能、分解能、受力、应力

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────────┐
│              Simulation MCP Server                          │
│              (FastMCP Server - Port 5003)                   │
│              SSE Endpoint: http://localhost:5003/sse        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  CrystaLLM   │    │  MatterSim   │    │  AI4Kappa    │
│              │    │              │    │              │
│ 结构生成      │    │ 弛豫+声子谱   │    │ 热导率计算    │
└──────────────┘    └──────────────┘    └──────────────┘
```

## 🔧 可用工具（8个）

### 1. 结构生成工具（2个）
- `generate_crystal_structure(composition)` - 从化学式生成晶体结构
- `extract_and_validate_cif(message_parts)` - 提取并验证用户提供的 CIF 文件

### 2. 结构弛豫工具（1个）
- `relax_structure(cif_content, optimizer="BFGS", max_steps=500, fmax=0.01)` - 结构弛豫

### 3. 声子谱工具（1个）
- `calculate_phonon(cif_content, supercell_matrix=[4,4,4])` - 计算声子谱（⚠️ 必须先弛豫）

### 4. 热导率工具（1个）
- `calculate_kappa_from_cif(cif_content, method="kappa_p", temperature=300.0)` - 计算热导率

### 5. 能量属性工具（1个）
- `calculate_energy_from_cif(cif_content)` - 计算形成能、分解能、受力、应力

## 🚀 快速开始

### 启动 Server
```bash
uv run python mcp_servers/simulation/server.py
```

Server 将在以下端点启动：
- **SSE Endpoint**: `http://localhost:5003/sse`
- **Health Check**: `http://localhost:5003/health`

## 📖 相关文档

- **Simulation Agent**: [agents/simulation_agent/README.md](../../agents/simulation_agent/README.md)
- **项目主文档**: [README.md](../../README.md)

## 📄 许可证

MIT License
