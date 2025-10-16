# Database MCP Server

## 📖 简介

Database MCP Server 是一个基于 FastMCP 构建的材料数据库查询服务器。它提供多数据库查询和结构获取功能。

## ✨ 核心特性

### 🔍 多数据库查询
- **Materials Project**: 材料数据库
- **OQMD**: 开放量子材料数据库
- **COD**: 晶体学开放数据库
- **AFLOW**: 自动流程材料数据库

## 🚀 快速开始

### 启动 Server
```bash
uv run python mcp_servers/database_call/server.py --port 50002
```

Server 将在以下端点启动：
- **SSE Endpoint**: `http://localhost:50002/sse`
- **Health Check**: `http://localhost:50002/health`

## 📖 相关文档

- **Database Agent**: [agents/database_agent/README.md](../../agents/database_agent/README.md)
- **项目主文档**: [README.md](../../README.md)

## 📄 许可证

MIT License
