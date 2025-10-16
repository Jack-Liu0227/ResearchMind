---
type: "manual"
---

# ResearchMind V2 - MCP 服务器最终修复总结

## 🎯 核心问题解决

### 原始问题
运行 MCP 服务器时出现 `TypeError: 'FastMCP' object is not callable`，无法被 MCP Inspector 检测到。

### 最终解决方案
采用标准的 `mcp.server.fastmcp.FastMCP` 而不是 `fastmcp.FastMCP`，并实现了真正的 ArXiv 搜索功能。

## 🚀 新的 Paper Search 服务器

### 主要特性
- ✅ **真实 ArXiv 搜索**: 使用 `arxiv` 库进行实际的论文搜索
- ✅ **MCP Inspector 兼容**: 使用 SSE 协议，可被 MCP Inspector 检测
- ✅ **数据持久化**: 论文信息保存到 JSON 文件
- ✅ **多种搜索方式**: 支持主题搜索和作者搜索
- ✅ **PDF 下载**: 支持直接下载论文 PDF
- ✅ **命令行参数**: 支持自定义端口、主机和日志级别

### 可用工具

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `search_arxiv_papers` | 根据主题搜索 ArXiv 论文 | topic, max_results |
| `get_paper_info` | 获取特定论文的详细信息 | paper_id |
| `list_saved_papers` | 列出所有已保存的论文 | topic (可选) |
| `download_paper` | 下载论文 PDF | paper_id, download_dir (可选) |
| `search_papers_by_author` | 根据作者搜索论文 | author_name, max_results |
| `health_check` | 健康检查 | 无 |

## 📋 依赖更新

### 新增依赖
```toml
# pyproject.toml 中添加
"arxiv>=1.4.0",
```

### 安装命令
```bash
uv sync
```

## 🔧 使用方式

### 1. 启动服务器
```bash
# 默认参数启动
uv run python mcp_servers/paper_search/server.py

# 自定义参数启动
uv run python mcp_servers/paper_search/server.py --port 5011 --host 0.0.0.0 --log-level DEBUG

# 查看帮助
uv run python mcp_servers/paper_search/server.py --help
```

### 2. MCP Inspector 连接
```bash
npx @modelcontextprotocol/inspector node build/index.js
```

连接 URL: `http://localhost:5001/sse` (或您指定的端口)

### 3. 环境变量配置
```bash
# 设置传输协议 (默认为 sse)
set MCP_TRANSPORT=sse

# 或使用 http
set MCP_TRANSPORT=http
```

## 📁 文件结构

### 新的服务器文件
```
mcp_servers/paper_search/
├── server.py          # 新的标准 MCP 服务器
└── server_old.py      # 原始服务器备份
```

### 论文数据存储
```
papers/
├── quantum_computing/
│   └── papers_info.json
├── machine_learning/
│   └── papers_info.json
└── downloads/
    ├── paper1.pdf
    └── paper2.pdf
```

## 🌟 实际使用示例

### 1. 搜索量子计算相关论文
```json
{
  "tool": "search_arxiv_papers",
  "arguments": {
    "topic": "quantum computing",
    "max_results": 5
  }
}
```

### 2. 获取论文详细信息
```json
{
  "tool": "get_paper_info",
  "arguments": {
    "paper_id": "2301.12345"
  }
}
```

### 3. 按作者搜索
```json
{
  "tool": "search_papers_by_author",
  "arguments": {
    "author_name": "John Preskill",
    "max_results": 10
  }
}
```

### 4. 下载论文 PDF
```json
{
  "tool": "download_paper",
  "arguments": {
    "paper_id": "2301.12345"
  }
}
```

## 🔄 与其他服务器的兼容性

### 其他 MCP 服务器状态
由于采用了新的架构，建议也更新其他服务器：

1. **materials服务器** - 可以改为使用 Materials Project API
2. **simulation服务器** - 可以集成真实的计算化学工具
3. **rdkit服务器** - 可以使用实际的 RDKit 功能

## ⚡ 性能优化

### 搜索缓存
- 论文信息自动缓存到本地 JSON 文件
- 避免重复搜索相同主题
- 支持离线查看已下载的论文信息

### 异步支持
- 虽然当前工具是同步的，但 FastMCP 支持异步工具
- 可以轻松扩展为异步版本以提高性能

## 🛠️ 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 使用不同端口
   uv run python mcp_servers/paper_search/server.py --port 5011
   ```

2. **ArXiv 库导入错误**
   ```bash
   # 重新安装依赖
   uv sync
   ```

3. **MCP Inspector 连接失败**
   - 确保使用正确的 SSE 端点: `http://localhost:5001/sse`
   - 检查防火墙设置
   - 确认服务器已正确启动

4. **论文下载失败**
   - 检查网络连接
   - 确认 paper_id 格式正确
   - 确保有足够的磁盘空间

### 日志调试
```bash
# 启用详细日志
uv run python mcp_servers/paper_search/server.py --log-level DEBUG
```

## 🎉 总结

现在 ResearchMind V2 拥有了一个功能完整的论文搜索 MCP 服务器：

✅ **真实功能** - 实际连接 ArXiv API 搜索论文  
✅ **MCP 兼容** - 完全兼容 MCP Inspector  
✅ **数据持久化** - 论文信息本地存储  
✅ **多样化工具** - 6 种不同的论文处理工具  
✅ **易于使用** - 命令行参数和环境变量支持  
✅ **文档完整** - 详细的使用说明和故障排除  

可以通过 Python 启动脚本安全地启动整个项目，并使用 MCP Inspector 进行测试和调试！🚀