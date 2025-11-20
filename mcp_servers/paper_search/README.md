# Paper Search MCP Server

## 📖 简介

> **2025-11 更新提示**
> - 默认 SSE 端口为 50004（`PAPER_SEARCH_MCP_PORT`）。
> - 推荐使用 `search_papers` 工具进行多源并行查询，`max_results` 控制每源条数。
> - 文件元数据中的 CSV/MD 下载链接改为 `/api/download/...` 相对路径，前端会补全域名并通过 Nginx 代理。

Paper Search MCP Server 是一个基于 FastMCP 构建的学术文献检索和分析服务器。它提供 18 个核心工具（并行检索 + 相对路径下载 + 上传文档转换），支持多源检索（ArXiv + Tavily）、智能分析、报告生成和向量化存储。

## ✨ 核心特性

### 🔍 多源检索
- **ArXiv API**：学术预印本搜索
- **Tavily API**：学术和网页搜索
- **Semantic Scholar API**：学术论文搜索
- **综合搜索**：使用 `search_papers` 工具综合检索所有源（支持并行查询）

### 📊 智能分析
- **批量分析**：自动提取摘要并翻译成中文
- **关键信息**：提取目标、方法、结果、创新点
- **汇总表格**：将论文列表保存为 Excel 表格

### 📝 报告生成
- **综合报告**：基于多篇论文生成研究报告
- **多种格式**：支持 IEEE、Nature、ArXiv 格式
- **完整内容**：包含执行摘要、背景、现状、方法、分析、问题、方案、展望、参考文献

### 💾 持久化存储
- **向量化存储**：将论文全文向量化存储到 ChromaDB
- **语义搜索**：支持自然语言追问文献内容
- **长期追问**：支持基于向量化存储的长期追问

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────────┐
│              Paper Search MCP Server                        │
│              (FastMCP Server - Port 50004)                  │
│              SSE Endpoint: http://localhost:50004/sse       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   ArXiv API  │    │  Tavily API  │    │  ChromaDB    │
│              │    │              │    │              │
│ 学术预印本    │    │ 学术+网页搜索 │    │ 向量数据库    │
└──────────────┘    └──────────────┘    └──────────────┘
```

## 🔧 可用工具（18个）

### 1. 规划工具（1个）

#### `generate_research_plan`
**功能**: 生成研究计划，优化搜索词

**参数**:
- `user_intent` (str): 用户意图描述

**返回**:
```json
{
  "success": true,
  "plan": {
    "original_intent": "量子计算",
    "optimized_keywords": ["quantum computing", "quantum algorithms"],
    "search_strategy": "综合搜索 ArXiv + Tavily",
    "expected_results": 10
  }
}
```

---

### 2. 检索工具（9个）

#### `ingest_uploaded_papers`（上传文档 → 文献条目）
**功能**: 将用户上传的文本 / PDF / DOCX 转换为 `source="upload"` 的论文条目，自动写入会话目录并生成 CSV。

**参数**:
- `files` (List[Dict]): 每个文件需要 `filename`、`content`（文本或 base64）、`encoding`（默认 utf-8）
- `session_id` (str, 可选): 指定会话 ID；未提供时自动生成
- `topic` (str, 可选): 会话主题（用于文件夹命名）

**返回**:
```json
{
  "status": "success",
  "session_id": "upload_20251024_xxxxxxxx",
  "total_results": 2,
  "csv_download_url": "/api/download/...",
  "papers": [
    {
      "paper_id": "upload_ab12cd34",
      "title": "用户上传的报告",
      "source": "upload",
      "preview": "..."
    }
  ]
}
```

---

#### `search_papers` ⭐ 推荐
**功能**: 统一的多源文献搜索接口（支持并行查询、自动去重、自动保存CSV）

**参数**:
- `query` (str): 搜索查询（支持多个检索词，用逗号、分号或换行符分隔）
- `sources` (List[str], 可选): 搜索源列表 ['arxiv', 'tavily_academic', 'tavily', 'semantic_scholar']，默认搜索所有源
- `max_results` (int): 每个源的最大结果数（默认 3）
- `session_id` (str, 可选): 会话ID（用于保存搜索结果到文件）
- `expand_query` (bool): 是否使用LLM自动生成多个检索词（默认 False）
- `num_expanded_queries` (int): 生成的检索词数量（默认 3）

**返回**:
```json
{
  "success": true,
  "total_results": 12,
  "sources_used": ["arxiv", "tavily_academic", "semantic_scholar"],
  "papers": [...],
  "saved_to": "session_data/papers/session_xxx/papers_xxx.csv"
}
```

---

#### `search_arxiv_papers`
**功能**: ArXiv 主题搜索

**参数**:
- `topic` (str): 搜索主题
- `max_results` (int): 最大结果数（默认 10）

**返回**:
```json
{
  "success": true,
  "total_results": 10,
  "papers": [
    {
      "id": "2401.12345",
      "title": "Quantum Computing Advances",
      "authors": ["John Doe", "Jane Smith"],
      "abstract": "...",
      "published": "2024-01-15",
      "url": "https://arxiv.org/abs/2401.12345",
      "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf"
    }
  ]
}
```

---

#### `search_papers_by_author`
**功能**: ArXiv 作者搜索

**参数**:
- `author_name` (str): 作者姓名
- `max_results` (int): 最大结果数（默认 10）

**返回**: 同 `search_arxiv_papers`

---

#### `get_paper_info`
**功能**: 获取单篇论文信息

**参数**:
- `paper_id` (str): 论文 ID（ArXiv ID）

**返回**: 单篇论文的详细信息

---

#### `tavily_search`
**功能**: 通用网页搜索

**参数**:
- `query` (str): 搜索查询
- `max_results` (int): 最大结果数（默认 5）

**返回**:
```json
{
  "success": true,
  "total_results": 5,
  "results": [
    {
      "title": "...",
      "url": "...",
      "content": "...",
      "score": 0.95
    }
  ]
}
```

---

#### `tavily_academic_search`
**功能**: 学术搜索

**参数**:
- `query` (str): 搜索查询
- `max_results` (int): 最大结果数（默认 5）

**返回**: 同 `tavily_search`

---

#### `tavily_news_search`
**功能**: 新闻搜索

**参数**:
- `query` (str): 搜索查询
- `max_results` (int): 最大结果数（默认 5）
- `days` (int): 搜索最近几天的新闻（默认 7）

**返回**: 同 `tavily_search`

---

### 3. 分析工具（2个）

#### `batch_paper_analysis`
**功能**: 批量分析论文，生成中文摘要

**参数**:
- `papers` (list): 论文列表
- `analysis_type` (str): 分析类型（默认 "summary"）

**返回**:
```json
{
  "success": true,
  "total_analyzed": 10,
  "analyses": [
    {
      "paper_id": "2401.12345",
      "summary_cn": "本文提出了一种新的量子计算算法...",
      "key_points": {
        "objective": "提出新的量子计算算法",
        "method": "基于量子纠缠的优化方法",
        "results": "性能提升 50%",
        "innovation": "首次将量子纠缠应用于优化问题"
      }
    }
  ]
}
```

---

#### `generate_research_report`
**功能**: 生成综合研究报告

**参数**:
- `paper_ids` (list): 论文 ID 列表
- `topic` (str): 研究主题
- `report_format` (str): 报告格式（默认 "ieee"）

**返回**:
```json
{
  "success": true,
  "report": {
    "title": "量子计算研究综述",
    "format": "ieee",
    "sections": {
      "executive_summary": "...",
      "background": "...",
      "current_state": "...",
      "methods": "...",
      "analysis": "...",
      "challenges": "...",
      "solutions": "...",
      "future_directions": "...",
      "references": [...]
    }
  }
}
```

---

### 4. 向量化工具（2个）

#### `ingest_papers_to_vector_store`
**功能**: 向量化存储论文

**参数**:
- `paper_ids` (list): 论文 ID 列表
- `collection_name` (str): 集合名称（默认 "papers"）

**返回**:
```json
{
  "success": true,
  "total_ingested": 10,
  "collection_name": "papers",
  "vector_count": 150
}
```

---

#### `semantic_search_papers`
**功能**: 语义搜索论文

**参数**:
- `query` (str): 搜索查询
- `top_k` (int): 返回结果数（默认 5）
- `collection_name` (str): 集合名称（默认 "papers"）

**返回**:
```json
{
  "success": true,
  "total_results": 5,
  "results": [
    {
      "paper_id": "2401.12345",
      "content": "...",
      "score": 0.95,
      "metadata": {...}
    }
  ]
}
```

---

### 5. 其他工具（2个）

#### `download_paper`
**功能**: 下载论文 PDF

**参数**:
- `paper_url` (str): 论文 URL
- `download_dir` (str): 下载目录（可选）

**返回**:
```json
{
  "success": true,
  "file_path": "/path/to/paper.pdf",
  "file_size": 1024000
}
```

---

## 🚀 快速开始

### 前置要求
- Python 3.11+
- UV (Python 包管理工具)
- Tavily API Key (可选，用于网页搜索)

### 安装依赖
```bash
uv sync
```

### 配置环境变量
创建 `.env` 文件：
```bash
# Tavily API Key (可选)
TAVILY_API_KEY=your_tavily_api_key_here
```

### 启动 Server
```bash
uv run python mcp_servers/paper_search/server.py --port 50004
```

Server 将在以下端点启动：
- **SSE Endpoint**: `http://localhost:50004/sse`
- **Health Check**: `http://localhost:50004/health`

## 📁 项目结构

```
mcp_servers/paper_search/
├── server.py               # MCP Server 实现
├── modules/                # 功能模块
│   ├── search/            # 搜索模块
│   │   ├── arxiv.py       # ArXiv 搜索
│   │   └── tavily.py      # Tavily 搜索
│   ├── report_generator/  # 报告生成模块
│   │   └── reporting.py   # 报告生成
│   └── context_manager/   # 上下文管理模块
│       └── ingestion.py   # 向量化存储
├── prompts.py              # 提示词
├── README.md               # 文档（本文件）
└── ARCHITECTURE.md         # 架构说明
```

## 🛠️ 技术栈

- **FastMCP**: MCP Server 开发框架
- **ArXiv API**: 学术预印本搜索
- **Tavily API**: 学术和网页搜索
- **ChromaDB**: 向量数据库
- **Uvicorn**: ASGI 服务器

## 📖 相关文档

- **Deep Research Agent**: [agents/deep_research/README.md](../../agents/deep_research/README.md)
- **项目主文档**: [README.md](../../README.md)
- **项目简介**: [INTRO.md](../../INTRO.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

