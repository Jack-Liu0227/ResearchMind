# Deep Research Agent – Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Deep Research Agent                      │
│     (Google ADK Agent, orchestrates literature workflows)   │
└─────────────────────────────────────────────────────────────┘
                           │  SSE
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Paper Search MCP Server (50004)             │
│  - Parallel ArXiv & Tavily search                           │
│  - Batch analysis & report generation                       │
│  - ChromaDB vector storage                                  │
│  - Relative `/api/download/...` file links                  │
└─────────────────────────────────────────────────────────────┘
```

## Components

| Module | Responsibility |
|--------|----------------|
| `agent.py` | Defines the ADK agent, routing user intents to MCP tools. |
| `prompts.py` | Houses system instructions guiding literature analysis. |
| Paper Search MCP | FastMCP server providing search/analysis/report tools. |

## Notable Behaviours

- Uses `search_papers_all_sources` as the default entry point, running ArXiv and Tavily queries in parallel.  
- Emits CSV/Markdown metadata with relative download URLs so the UI can resolve `http(s)://<host>/api/...`.  
- `batch_paper_analysis` and `generate_research_report` create files under `papers/<session_id>/` for reuse.  
- Vector ingestion enables follow-up semantic queries without repeating external API calls.

## Ports & Environment

```
PAPER_SEARCH_MCP_PORT=50004
PAPER_SEARCH_MCP_URL=http://localhost:50004/sse
```

The agent expects the Services layer (HTTP 50002 / WS 50003) to proxy downloads through `/api/download/...`.
