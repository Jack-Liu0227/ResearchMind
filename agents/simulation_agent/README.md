# Simulation Agent (仿真计算助手)

## 简介

Simulation Agent 基于 Google ADK 实现，通过 MCP (Model Context Protocol) 与 Simulation MCP Server 协作，可完成晶体结构生成、结构弛豫、声子谱计算、热导率计算以及能量属性评估等任务。

> ### 2025-10 更新
> - Simulation MCP Server 默认监听端口更新为 `50005`（`SIMULATION_MCP_PORT`）。  
> - `calculate_kappa_from_cif` 与 `batch_calculate_kappa` 支持 `session_id` / `keep_files` 参数，可在会话目录下生成独立工作目录并按需保留中间文件。  
> - 新增批量热导率工具，可一次性对多个结构运行 AI4Kappa，复用同一工作目录以降低 I/O。

## 核心能力

- **晶体结构生成**：基于 CrystaLLM，根据化学式输出 CIF，自动校验结构有效性。  
- **结构弛豫**：调用 MatterSim（ASE BFGS / FIRE / LBFGS 等优化器）最小化能量，并输出弛豫前后的能量变化。  
- **声子谱计算**：基于 MatterSim 生成声子色散与声子态密度（DOS），要求先完成结构弛豫。  
- **热导率计算**：集成 AI4Kappa，支持 Slack 模型 (Kappa-P) 与 ML 模型 (Kappa-MTP)，可指定温度、会话 ID，并保留中间文件进行调试。  
- **能量属性**：输出形成能、分解能、原子受力、应力等信息，建议先弛豫结构以提高准确性。

## MCP 端工具

| 分类 | 工具 | 说明 |
| ---- | ---- | ---- |
| 结构生成 | `generate_crystal_structure` | 根据化学式生成结构（默认返回 CIF & 前端结构数据） |
|  | `extract_and_validate_cif` | 解析上传的 CIF，自动 base64 解码与规范化 |
| 结构弛豫 | `relax_structure` | 支持 BFGS/FIRE/LBFGS，默认 `fmax=0.01`，返回弛豫后 CIF |
| 声子谱 | `calculate_phonon` | 输入弛豫后的 CIF，输出声子带结构、DOS 及图像 |
| 热导率 | `calculate_kappa_from_cif` | 单体热导率计算，可指定 `session_id`、`keep_files`、`method`、`temperature` |
|  | `batch_calculate_kappa` | 批量 κ 计算，对结构列表统一写入工作目录并返回整体摘要 |
| 能量属性 | `calculate_energy_from_cif` | 输出形成能、分解能、受力、应力等指标 |

## 常用流程

1. **生成结构并计算声子谱**  
   `generate_crystal_structure` → `relax_structure` → `calculate_phonon`

2. **生成结构并计算热导率**  
   `generate_crystal_structure` → `relax_structure` → `calculate_kappa_from_cif`

3. **批量热导率分析**  
   准备结构列表（含 `cifContent`、`formula`、`id`），调用 `batch_calculate_kappa`，可设置 `keep_files=True` 保留工作目录。

4. **上传结构并计算能量/热导率**  
   `extract_and_validate_cif` → `relax_structure`（如需） → `calculate_energy_from_cif` / `calculate_kappa_from_cif`

## 启动步骤

1. **安装依赖**
   ```bash
   uv sync
   ```

2. **配置环境变量**
   ```bash
   echo "GOOGLE_API_KEY=your_google_api_key" >> .env
   ```

3. **启动 Simulation MCP Server**
   ```bash
   uv run python mcp_servers/simulation/server.py
   ```

4. **启动 Simulation Agent**
   ```bash
   uv run python agents/simulation_agent/agent.py
   ```

## 参考文档

- [Simulation MCP Server](../../mcp_servers/simulation/README.md)  
- [项目总览 README](../../README.md)  
- [项目概览 INTRO](../../INTRO.md)

## 许可

MIT License
