# Database Agent – Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Database Agent                         │
│         (Google ADK Agent for materials databases)          │
└─────────────────────────────────────────────────────────────┘
                           │  SSE
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           Database MCP Server – http://localhost:50006/sse  │
│  • Materials Project REST wrappers                          │
│  • OQMD / COD / AFLOW clients                               │
│  • Structure normalisation & property aggregation           │
│  • Delegation to Simulation MCP when entries are missing    │
└─────────────────────────────────────────────────────────────┘

        ┌──────────────────────────────┐
        │ Simulation MCP (50005)       │  ← fallback
        │ CrystaLLM / AI4Kappa /       │
        │ MatterSim for generated data │
        └──────────────────────────────┘
```

## Key Modules

| File | Purpose |
|------|---------|
| `agent.py` | Defines the ADK agent, routing user requests to MCP tools. |
| `prompts.py` | Prompts guiding how results are summarised for the UI. |
| Database MCP (`mcp_servers/database_call`) | FastMCP server providing search & retrieval tools. |

## Highlights

- Consolidates results from multiple databases into a consistent schema.  
- Emits CIF/metadata download information using `/api/download/...` relative paths.  
- When no database entry is found, invokes Simulation MCP to generate a candidate structure, clearly flagging the origin.  
- Designed to work alongside Services HTTP (50002) and WebSocket (50003) endpoints.

## Environment Variables

```
DATABASE_MCP_HOST=127.0.0.1
DATABASE_MCP_PORT=50006
DATABASE_MCP_URL=http://localhost:50006/sse
```
