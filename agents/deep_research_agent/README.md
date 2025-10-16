# Deep Research Agent (深度研究助手)

## 📖 简介

Deep Research Agent 是一个基于 Google ADK 构建的学术文献研究助手。它通过 MCP (Model Context Protocol) 与 Paper Search MCP Server 通信，提供从文献检索、分析到报告生成的完整研究流程。

## ✨ 核心特性

### 🔍 多源检索
- **默认综合检索**：优先使用 `search_papers_all_sources` 综合检索 ArXiv + Tavily
- **单独检索**：支持指定特定来源（ArXiv、Tavily Academic、Tavily Web）
- **智能规划**：自动优化搜索词（中文→英文）

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
│                  Deep Research Agent                        │
│                  (Google ADK Agent)                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (SSE Transport)
┌─────────────────────────────────────────────────────────────┐
│              Paper Search MCP Server                        │
│              (FastMCP Server - Port 50001)                  │
│                                                             │
│  13 个核心工具:                                              │
│  - 规划类 (1个): generate_research_plan                     │
│  - 检索类 (8个): search_papers_all_sources, ...            │
│  - 分析类 (2个): batch_paper_analysis, ...                 │
│  - 向量化 (2个): ingest_papers_to_vector_store, ...        │
│  - 其他 (1个): download_paper                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              External Services                              │
│  - ArXiv API (学术预印本)                                   │
│  - Tavily API (学术和网页搜索)                              │
│  - ChromaDB (向量数据库)                                    │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 可用工具（13个）

### 1. 规划工具（1个）
- `generate_research_plan(user_intent)` - 生成研究计划，优化搜索词

### 2. 检索工具（8个）
- `search_papers_all_sources(topic, max_results_per_source=5)` - **综合搜索所有源（推荐）**
- `search_arxiv_papers(topic, max_results)` - ArXiv 主题搜索
- `search_papers_by_author(author_name, max_results)` - ArXiv 作者搜索
- `get_paper_info(paper_id)` - 获取单篇论文信息
- `tavily_search(query, max_results)` - 通用网页搜索
- `tavily_academic_search(query, max_results)` - 学术搜索
- `tavily_news_search(query, max_results, days)` - 新闻搜索

### 3. 分析工具（2个）
- `batch_paper_analysis(papers, analysis_type="summary")` - 批量分析论文，生成中文摘要
- `generate_research_report(paper_ids, topic, report_format="ieee")` - 生成综合研究报告

### 4. 向量化工具（2个）
- `ingest_papers_to_vector_store(paper_ids, collection_name)` - 向量化存储论文
- `semantic_search_papers(query, top_k, collection_name)` - 语义搜索论文

### 5. 其他工具（1个）
- `download_paper(paper_url, download_dir)` - 下载论文 PDF

## 📋 工作流程

### 标准流程
1. **规划**：`generate_research_plan(user_intent)` - 优化搜索词
2. **搜索**：`search_papers_all_sources(topic, max_results_per_source=5)` - 综合检索（默认）
3. **分析**：`batch_paper_analysis(papers, analysis_type="summary")` - 生成中文摘要
4. **报告**（可选）：`generate_research_report(paper_ids, topic)` - 生成综合报告
5. **向量化**（可选）：`ingest_papers_to_vector_store(paper_ids, collection_name)` - 持久化存储
6. **追问**（可选）：`semantic_search_papers(query, top_k, collection_name)` - 长期追问

## 🎯 使用示例

### 示例 1：综合搜索（默认）
```
用户："搜索量子计算相关的论文"

步骤：
1. generate_research_plan(user_intent="量子计算")
   → 获得优化搜索词："quantum computing"
2. search_papers_all_sources(topic="quantum computing", max_results_per_source=5)
   → 获得综合搜索结果（ArXiv + Tavily）
3. 向用户展示论文列表（标题、作者、摘要）
```

### 示例 2：综合搜索并生成报告
```
用户："搜索量子计算相关的论文并生成报告"

步骤：
1. generate_research_plan(user_intent="量子计算")
2. search_papers_all_sources(topic="quantum computing", max_results_per_source=5)
3. batch_paper_analysis(papers=[...], analysis_type="summary")
4. generate_research_report(paper_ids=[...], topic="量子计算")
5. 向用户展示报告内容
```

### 示例 3：向量化存储并追问
```
用户："将这些论文向量化存储，然后告诉我哪些提到了量子纠缠"

步骤：
1. ingest_papers_to_vector_store(paper_ids=[...], collection_name="quantum")
   → 向量化存储论文
2. semantic_search_papers(query="量子纠缠", top_k=5, collection_name="quantum")
   → 从向量化存储中搜索相关内容
3. 向用户展示搜索结果
```

## 🚀 快速开始

### 前置要求
- Python 3.11+
- UV (Python 包管理工具)
- Google API Key (用于 Gemini 2.0 Flash)
- Tavily API Key (可选，用于网页搜索)

### 安装依赖
```bash
uv sync
```

### 配置环境变量
创建 `.env` 文件：
```bash
# Google API Key
GOOGLE_API_KEY=your_google_api_key_here

# Tavily API Key (可选)
TAVILY_API_KEY=your_tavily_api_key_here
```

### 启动 Paper Search MCP Server
```bash
uv run python mcp_servers/paper_search/server.py --port 50001
```

### 启动 Deep Research Agent
```bash
uv run python agents/deep_research/agent.py
```

## 📁 项目结构

```
agents/deep_research/
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
- **ChromaDB**: 向量数据库
- **ArXiv API**: 学术预印本搜索
- **Tavily API**: 学术和网页搜索

## 📖 相关文档

- **Paper Search MCP Server**: [mcp_servers/paper_search/README.md](../../mcp_servers/paper_search/README.md)
- **项目主文档**: [README.md](../../README.md)
- **项目简介**: [INTRO.md](../../INTRO.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

