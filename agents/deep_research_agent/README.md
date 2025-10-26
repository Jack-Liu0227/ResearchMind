# Deep Research Agent

The Deep Research Agent orchestrates literature discovery, analysis, and report writing through the Paper Search MCP Server.

> **October 2025 refresh**
> - Paper Search MCP now listens on `50004` (`PAPER_SEARCH_MCP_PORT`); the SSE endpoint is `http://localhost:50004/sse`.
> - `search_papers_all_sources` performs parallel ArXiv + Tavily requests, with `max_results_per_source` controlling the cap per backend.
> - CSV/Markdown download metadata is emitted as `/api/download/...` relative paths so the frontend (or Nginx) can attach the correct host.
> - 新增 `ingest_uploaded_papers` 工具，可将用户上传的文本/PDF/DOCX 转换为可用于分析和报告的文献条目。

## Capabilities

- **Multi-source search**: ArXiv, Tavily Academic, Tavily Web, or combined queries with automatic keyword optimisation (Chinese → English).  
- **Batch analysis**: Extracts abstracts, produces Chinese summaries, and compiles key findings (objective/method/result/innovation).  
- **Report generation**: Creates comprehensive reports covering background, current status, techniques, gaps, and references.  
- **Vector storage**: Ingests full texts into ChromaDB to support semantic follow-up questions.

## Key MCP Tools

| Tool | Description |
|------|-------------|
| `generate_research_plan` | Optimises search queries for the target topic. |
| `ingest_uploaded_papers` | Converts uploaded documents into `source="upload"` papers and saves CSV/metadata. |
| `search_papers_all_sources` | Parallel ArXiv + Tavily retrieval with per-source result limits. |
| `search_arxiv_papers`, `search_papers_by_author`, `tavily_*` | Source-specific lookups when needed. |
| `batch_paper_analysis` | Summarises papers, produces CSV/MD output (relative download URLs). |
| `batch_paper_analysis` | Saves condensed Chinese summaries and key info. |
| `generate_research_report` | Builds full reports (IEEE/Nature/ArXiv style). |
| `save_papers_to_csv`, `fetch_paper_content` | Utility helpers for downstream processing. |

## Typical Workflow

0. 如果用户上传文档，先调用 `ingest_uploaded_papers` 将附件转换为标准文献条目（返回的 CSV 路径可沿用后续步骤）。

1. `generate_research_plan` (optional) to refine keywords.  
2. `search_papers_all_sources` to gather literature.  
3. `batch_paper_analysis` to summarise and produce CSV/MD assets.  
4. `generate_research_report` for a consolidated write-up.  
5. Optional vector ingestion for semantic Q&A.

## Start-Up

```bash
# ensure dependencies
uv sync

# start Paper Search MCP (port 50004)
uv run python mcp_servers/paper_search/server.py --port 50004

# launch Deep Research Agent
uv run python agents/deep_research_agent/agent.py
```

## Related Docs

- [Paper Search MCP README](../../mcp_servers/paper_search/README.md)  
- [Deep Research Agent Architecture](./ARCHITECTURE.md)

## License

MIT License
