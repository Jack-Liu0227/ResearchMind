# Database Agent

The Database Agent queries multiple materials databases via the Database MCP Server and can invoke the Simulation Agent when structures need to be generated.

> **October 2025 refresh**
> - Database MCP listens on `50006` (`DATABASE_MCP_PORT`); SSE endpoint: `http://localhost:50006/sse`.  
> - Response payloads record whether a structure was fetched or generated.  
> - CIF downloads share the same `/api/download/...` relative path convention as other agents.

## Capabilities

- **Multi-database search**: Materials Project, OQMD, COD, AFLOW, and any additional providers configured in the MCP.  
- **Structure retrieval**: Returns CIF data plus key properties (band gap, formation energy, density, etc.).  
- **Automatic fallback**: When a target is absent, triggers Simulation MCP to generate a plausible structure.  
- **Property aggregation**: Normalises result formats so downstream agents or the UI can display comparable metadata.

## MCP Tools (Examples)

| Tool | Description |
|------|-------------|
| `search_materials_project`, `search_oqmd`, `search_cod`, `search_aflow` | Source-specific queries. |
| `search_all_databases` | Convenience wrapper that tries each provider in turn. |
| `get_structure_details` | Returns full CIF + property bundle. |
| `generate_structure_if_missing` | Delegates to Simulation MCP when no entry exists. |

## Typical Workflow

1. Search Materials Project (or combined search) for the desired composition or mp-id.  
2. If found, return CIF + properties.  
3. If missing, automatically call Simulation Agent → CrystaLLM to seed a structure, then relay the generated CIF.  
4. Optionally kick off Simulation Agent for relaxation/analysis.

## Start-Up

```bash
# dependencies
uv sync

# Database MCP (port 50006)
uv run python mcp_servers/database_call/server.py --port 50006

# Database Agent
uv run python agents/database_agent/agent.py
```

## Related Docs

- [Database MCP README](../../mcp_servers/database_call/README.md)  
- [Database Agent Architecture](./ARCHITECTURE.md)

## License

MIT License
