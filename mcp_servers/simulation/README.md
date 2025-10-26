# Simulation MCP Server

FastMCP 驱动的材料仿真服务端，负责为 Simulation Agent 提供结构生成、弛豫、声子谱、热导率及能量属性等工具。

> ### 2025-10 更新
> - 默认监听端口更新为 `50005`（`SIMULATION_MCP_PORT`），SSE 端点 `http://localhost:50005/sse`。  
> - 热导率工具新增 `session_id` / `keep_files` 参数，并提供批量计算接口，支持共享工作目录和文件保留。  
> - 文件下载接口统一返回 `/api/download/...` 相对路径，适配前端与 Nginx 代理。

## 工具概览（共 8 个）

| 类别 | 工具 | 描述 |
| ---- | ---- | ---- |
| 结构生成 | `generate_crystal_structure` | 使用 CrystaLLM 根据化学式生成 CIF 与前端结构数据 |
|  | `extract_and_validate_cif` | 解析/验证上传的 CIF，自动 base64 解码与规范化 |
| 结构弛豫 | `relax_structure` | 调用 MatterSim (ASE) 优化结构，输出弛豫后 CIF 与能量变化 |
| 声子谱 | `calculate_phonon` | 生成声子色散、DOS 及对应图像（需先弛豫） |
| 热导率 | `calculate_kappa_from_cif` | 单体热导率计算，支持 `session_id`、`keep_files`、`method`、`temperature` |
|  | `batch_calculate_kappa` | 批量热导率计算，复用工作目录并返回总结数据 |
| 能量属性 | `calculate_energy_from_cif` | 生成形成能、分解能、受力、应力等指标 |
| 辅助 | `extract_and_validate_cif` |（同上）|

## 典型流程

1. **生成 → 弛豫 → 声子谱**  
   `generate_crystal_structure` → `relax_structure` → `calculate_phonon`

2. **生成 → 弛豫 → 热导率**  
   `generate_crystal_structure` → `relax_structure` → `calculate_kappa_from_cif`

3. **批量热导率**  
   准备结构列表（含 `cifContent` / `formula` / `id`），调用 `batch_calculate_kappa`，可设置 `keep_files=True` 在会话目录中保留输入输出。

4. **上传结构 → 能量/热导率**  
   `extract_and_validate_cif` → `relax_structure`（可选） → `calculate_energy_from_cif` / `calculate_kappa_from_cif`

## 端口与环境变量

```env
SIMULATION_MCP_HOST=127.0.0.1
SIMULATION_MCP_PORT=50005
SIMULATION_MCP_URL=http://localhost:50005/sse
```

SSE 端点：`http://localhost:50005/sse`  
健康检查：`http://localhost:50005/health`

## 启动

```bash
uv sync
uv run python mcp_servers/simulation/server.py
```

## 关联文档

- [Simulation Agent README](../../agents/simulation_agent/README.md)  
- [Simulation MCP Architecture](./ARCHITECTURE.md)

## 许可

MIT License
