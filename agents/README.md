# ResearchMind Agents

ResearchMind coordinates three Google ADK agents that specialise in literature discovery, database retrieval, and simulation workflows. Each agent connects to its companion MCP server via SSE and collaborates with the Services layer to deliver end-to-end materials research.

> **October 2025 refresh**
> - Paper Search MCP now listens on `50004` and returns `/api/download/...` relative paths so the UI or Nginx can resolve the host automatically.
> - Database MCP keeps its SSE endpoint on `50006`; the agent falls back to Simulation MCP for structure generation when a record is missing.
> - Simulation MCP listens on `50005` and supports session-scoped working directories plus batch thermal-conductivity runs.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                Research Coordinator Agent                   │
│            (Routes requests across specialised agents)      │
└─────────────────────────────────────────────────────────────┘
                     │             │             │
         ┌───────────┘             │             └───────────┐
         ▼                         ▼                         ▼
┌────────────────┐     ┌────────────────┐        ┌────────────────┐
│ Deep Research   │     │ Database       │        │ Simulation     │
│ Agent           │     │ Agent          │        │ Agent          │
│ (Literature)    │     │ (Materials DB) │        │ (Computation)  │
└──────┬──────────┘     └──────┬─────────┘        └──────┬────────┘
       │                         │                         │
       ▼                         ▼                         ▼
┌──────────────┐    ┌────────────────────┐     ┌────────────────────┐
│ Paper Search │    │ Database MCP       │     │ Simulation MCP      │
│ MCP (50004)  │    │ (50006)            │     │ (50005)             │
│ - ArXiv      │    │ - MaterialsProj.   │     │ - CrystaLLM         │
│ - Tavily     │    │ - OQMD / COD /     │     │ - AI4Kappa          │
│ - Vector DB  │    │   AFLOW            │     │ - MatterSim         │
└──────────────┘    └────────────────────┘     └────────────────────┘
```

## Agents at a Glance

| Agent | Primary MCP | Key Responsibilities | Updated Highlights |
|-------|-------------|----------------------|--------------------|
| Deep Research | Paper Search MCP (`50004`) | Optimises queries, runs parallel ArXiv + Tavily searches, summarises findings, generates reports, exposes vector search. | Returns CSV/MD download metadata as `/api/download/...` relative paths so the UI resolves the host. |
| Database | Materials Database MCP (`50006`) | Queries Materials Project, OQMD, COD, AFLOW; fetches CIF structures and properties; falls back to Simulation Agent when records are absent. | Quick-start uses `uv run ... --port 50006`; agent advertises when a structure is generated instead of fetched. |
| Simulation | Simulation MCP (`50005`) | Generates structures with CrystaLLM, performs relaxation, phonon calculations, thermal conductivity, and energy analysis. | `calculate_kappa_from_cif`/`batch_calculate_kappa` accept `session_id` + `keep_files`, enabling session-scoped temp dirs and batch κ runs. |

## Port Summary

```
Paper Search MCP    50004  (SSE endpoint http://localhost:50004/sse)
Database MCP        50006  (SSE endpoint http://localhost:50006/sse)
Simulation MCP      50005  (SSE endpoint http://localhost:50005/sse)
Services HTTP       50002  (internal)
Services WebSocket  50003  (internal)
Frontend (proxied)  50001  → VITE_FRONTEND_PORT (default 50010)
```

## Documentation Index

- Deep Research Agent  
  - [README](./deep_research_agent/README.md)  
  - [ARCHITECTURE](./deep_research_agent/ARCHITECTURE.md)

- Database Agent  
  - [README](./database_agent/README.md)  
  - [ARCHITECTURE](./database_agent/ARCHITECTURE.md)

- Simulation Agent  
  - [README](./simulation_agent/README.md)  
  - [ARCHITECTURE](./simulation_agent/ARCHITECTURE.md)

Refer to the project root `README.md` for environment variables and start-up scripts, and to the `services/README.md` for the websocket/HTTP bridge that connects the agents to the frontend.
