# Database Agent (数据库检索助手)

## 📖 简介

Database Agent 是一个基于 Google ADK 构建的材料数据库检索助手。它通过 MCP 与 Database MCP Server 通信，提供多数据库查询和结构获取功能。

## ✨ 核心特性

### 🔍 多数据库查询
- **Materials Project**: 材料数据库
- **OQMD**: 开放量子材料数据库
- **COD**: 晶体学开放数据库
- **AFLOW**: 自动流程材料数据库

### 📊 结构获取
- **CIF 格式**：获取晶体结构（CIF 格式）
- **属性查询**：查询材料属性（能带隙、形成能、密度等）

### 🤖 自动生成
- **自动生成**：数据库查询失败时自动调用 Simulation Agent 生成结构

## 🚀 快速开始

### 启动 Database MCP Server
```bash
uv run python mcp_servers/database_call/server.py --port 50002
```

### 启动 Database Agent
```bash
uv run python agents/database_agent/agent.py
```

## 📖 相关文档

- **Database MCP Server**: [mcp_servers/database_call/README.md](../../mcp_servers/database_call/README.md)
- **项目主文档**: [README.md](../../README.md)

## 📄 许可证

MIT License
