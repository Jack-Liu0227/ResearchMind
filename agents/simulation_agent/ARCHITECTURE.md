# Simulation Agent – Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Simulation Agent                         │
│      (Google ADK Agent for structure & property tasks)      │
└─────────────────────────────────────────────────────────────┘
                           │  SSE
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           Simulation MCP Server – http://localhost:50005/sse│
│  • CrystaLLM structure generation                           │
│  • MatterSim relaxation / phonons / energy analysis         │
│  • AI4Kappa κ calculations (single & batch)                 │
│  • Session-scoped working directories & keep_files support  │
└─────────────────────────────────────────────────────────────┘
```

## Components

| Module | Responsibility |
|--------|----------------|
| `agent.py` | Interprets user intent, orchestrates MCP tool calls, streams progress. |
| `prompts.py` | System prompts for safe and consistent simulation guidance. |
| Simulation MCP (`mcp_servers/simulation`) | FastMCP server hosting the toolset. |

## Notable Behaviours

- Accepts `session_id` when invoking κ tools; Simulation MCP places temporary files in `session_data/structures/<session>/thermal_conductivity`.  
- `keep_files=True` returns the working directory path so users can inspect inputs/outputs.  
- `batch_calculate_kappa` reuses a single directory for all CIFs to reduce overhead.  
- Image / CSV / MD assets are referenced via `/api/download/...` relative paths for compatibility with the Services proxy.

## Environment

```
SIMULATION_MCP_HOST=127.0.0.1
SIMULATION_MCP_PORT=50005
SIMULATION_MCP_URL=http://localhost:50005/sse
```

The agent depends on Services HTTP (50002) and WebSocket (50003) to deliver artefacts to the frontend.
