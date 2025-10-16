---
type: "manual"
---

# ResearchMind System Architecture

## Overview

ResearchMind is a multi-agent research assistant system built on Google's Agent Development Kit (ADK). The system follows a modular, microservices-inspired architecture with clear separation between the agent layer, tool servers, communication layer, and user interface.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                    (React + TypeScript)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │ WebSocket/HTTP
┌─────────────────────▼───────────────────────────────────────┐
│                    Communication Layer                       │
│              (FastAPI + WebSocket Server)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Multi-Agent System                         │
│              (DeepSeek-Chat as Default LLM)                 │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │Literature│ │ Database │ │Simulation│                   │
│  │  Agent   │ │  Agent   │ │  Agent   │                   │
│  │          │ │          │ │          │                   │
│  │DeepSeek  │ │DeepSeek  │ │DeepSeek  │                   │
│  │ + ADK    │ │ + ADK    │ │ + ADK    │                   │
│  └──────────┘ └──────────┘ └──────────┘                   │
└─────────────────────┬───────────────────────────────────────┘
                      │ MCP Protocol
┌─────────────────────▼───────────────────────────────────────┐
│                     MCP Tool Servers                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │  Paper   │ │Materials │ │Simulation│ │   Data   │     │
│  │  Search  │ │ Database │ │  Engine  │ │ Analysis │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │  RDKit   │ │Structure │ │Experiment│ │   ...    │     │
│  │  Tools   │ │Generator │ │  Design  │ │  Server  │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└──────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. User Interface Layer

**Technology Stack:**
- React 18+ with TypeScript
- Tailwind CSS for styling
- Vite for build tooling
- WebSocket client for real-time communication

**Key Features:**
- Real-time chat interface for agent interaction
- Visual representation of research results
- Task progress monitoring
- Multi-agent conversation management

**Directory:** `ui/`

### 2. Communication Layer

**Purpose:** Bridges the frontend and backend, managing all inter-component communication.

**Components:**
- **API Server** (`api_server.py`): FastAPI-based REST endpoints
- **WebSocket Server** (`websocket_server.py`): Real-time bidirectional communication
- **Client Utilities** (`client.py`): Helper functions for service communication
- **Configuration** (`config.py`): Centralized configuration management

**Key Responsibilities:**
- Request routing between UI and agents
- Session management
- Message queuing and delivery
- Authentication and authorization (future)

**Directory:** `communication/`

### 3. Agent Layer (Google ADK)

**Framework:** Google Agent Development Kit (ADK)

**Agent Types:**

### Agent System Overview

The ResearchMind system uses a **decentralized multi-agent architecture** where each agent operates independently using **DeepSeek-Chat** as the default language model, with Google ADK providing the agent framework. This design eliminates the need for a central orchestrator, allowing direct communication between agents and the frontend.

#### Literature Agent
- **Role:** Literature research and analysis
- **Capabilities:**
  - Paper search across multiple databases
  - Citation network analysis
  - Summarization and key insights extraction
  - Reference management

#### Database Agent
- **Role:** Materials and chemical database interaction
- **Capabilities:**
  - Query materials properties
  - Structure search and retrieval
  - Data aggregation from multiple sources

#### Simulation Agent
- **Role:** Computational simulation setup and analysis
- **Capabilities:**
  - Simulation parameter configuration
  - Job submission and monitoring
  - Results analysis and visualization

**Directory:** `agents/`

### 4. MCP Tool Servers

**Protocol:** Model Context Protocol (MCP)

**Server Types:**

#### Paper Search Server
- ArXiv integration
- Google Scholar API
- PubMed search
- Citation extraction

#### Materials Database Server
- Materials Project API
- OQMD interface
- JARVIS database
- Custom database connections

#### Simulation Server
- VASP input generation
- Gaussian job setup
- LAMMPS configuration
- Queue system integration

#### Data Analysis Server
- Statistical analysis tools
- Machine learning models
- Visualization generation
- Report creation

#### RDKit Server
- Molecular property calculation
- Structure manipulation
- SMILES/InChI conversion
- Conformer generation

**Directory:** `mcp_servers/`

## Data Flow

### 1. User Query Processing (Decentralized)

```
User Input → UI → WebSocket → Communication Layer → Specific Agent
                                                          ↓
                                                   Direct Processing
                                                          ↓
                                                 Tool Selection & Execution
```

### 2. Agent Task Execution

```
Specialized Agent → MCP Tool Request → Tool Server
                          ↓                 ↓
                    Tool Execution    External API/DB
                          ↓                 ↓
                    Tool Response ← ─ ─ ─ ─ ┘
                          ↓
                    Agent Processing
                          ↓
                    Result Generation
```

### 3. Response Delivery (Direct)

```
Agent Result → Communication Layer → WebSocket → UI
                    ↓
            Format & Validate
                    ↓
            Real-time Streaming
```

## Communication Protocols

### WebSocket Protocol

**Message Format:**
```json
{
  "id": "unique-message-id",
  "type": "request|response|notification",
  "timestamp": "ISO-8601",
  "source": "client|agent",
  "target": "agent-name|client",
  "payload": {
    "action": "action-type",
    "data": {}
  }
}
```

### MCP Protocol

**Tool Invocation:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {}
  },
  "id": "request-id"
}
```

## Security Considerations

### Current Implementation
- Environment-based API key management
- Local-only deployment
- No authentication (development phase)

### Future Enhancements
- JWT-based authentication
- Role-based access control
- API rate limiting
- Encrypted communication channels
- Audit logging

## Scalability Design

### Horizontal Scaling
- Stateless agent design
- Independent MCP servers
- Load balancer ready architecture

### Vertical Scaling
- Async processing throughout
- Resource pooling for tools
- Caching layer for frequent queries

## Deployment Architecture

### Development Environment
```
All components run locally:
- Agents: localhost:8000 (ADK web)
- UI: localhost:5173 (Vite dev server)
- MCP Servers: localhost:5000X (individual ports)
```

### Production Environment (Future)
```
Container-based deployment:
- Each component in Docker container
- Kubernetes orchestration
- Service mesh for communication
- External load balancer
```

## Configuration Management

### Environment Variables
- `.env` file for local development
- Separate configs per environment
- Secrets management via vault (future)

### Service Discovery
- Static configuration (current)
- Dynamic service registry (future)

## Monitoring and Observability

### Current Implementation
- Console logging
- Basic health checks
- Error reporting

### Future Enhancements
- Distributed tracing (OpenTelemetry)
- Metrics collection (Prometheus)
- Log aggregation (ELK stack)
- Performance monitoring

## Development Workflow

### Adding New Agents
1. Create agent directory in `agents/`
2. Implement agent class extending base
3. Define agent tools and capabilities
4. Register with root agent
5. Update communication routing

### Adding New Tools
1. Create MCP server in `mcp_servers/`
2. Implement tool functions
3. Define tool schemas
4. Test server independently
5. Register with relevant agents

### Frontend Development
1. Create React components in `ui/src/`
2. Implement WebSocket handlers
3. Add routing if needed
4. Style with Tailwind CSS
5. Test with mock data

## Testing Strategy

### Unit Testing
- Agent logic testing
- Tool function testing
- Component testing (UI)

### Integration Testing
- Agent-tool integration
- Communication layer testing
- End-to-end workflows

### Performance Testing
- Load testing for concurrent users
- Tool response time monitoring
- Memory usage profiling

## Technology Decisions

### Why DeepSeek-Chat as Default?
- **Cost-effective**: Competitive pricing for high-quality responses
- **Performance**: Excellent reasoning capabilities for research tasks
- **OpenAI-compatible**: Easy integration with existing tooling
- **Chinese language support**: Native support for multilingual research
- **Research focus**: Optimized for analytical and technical tasks

### Multi-Model Architecture
- **Flexibility**: Support for DeepSeek, OpenAI, Google Gemini, and Anthropic Claude
- **Failover**: Automatic fallback to alternative models if needed
- **Specialization**: Different models for different task types
- **Cost optimization**: Choose the most cost-effective model per task

### Why Google ADK?
- Modern agent framework
- Built-in tool management
- Standardized agent patterns
- Active development and support

### Why MCP?
- Standard protocol for tool integration
- Language-agnostic tool servers
- Reusable tool ecosystem
- Clear separation of concerns

### Why React + TypeScript?
- Type safety for complex UIs
- Rich ecosystem
- Excellent developer experience
- Modern build tools

### Why FastAPI?
- Native async support
- Automatic API documentation
- WebSocket support
- High performance

## Future Roadmap

### Phase 1 (Current)
- ✅ Core agent implementation
- ✅ Basic UI
- ✅ Essential tool servers
- ✅ Local deployment

### Phase 2
- [ ] Authentication system
- [ ] Enhanced UI features
- [ ] Additional tool servers
- [ ] Cloud deployment ready

### Phase 3
- [ ] Multi-user support
- [ ] Collaboration features
- [ ] Advanced analytics
- [ ] Plugin system

### Phase 4
- [ ] Enterprise features
- [ ] Advanced security
- [ ] Custom model integration
- [ ] Workflow automation

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Code style and standards
- Testing requirements
- Pull request process
- Architecture decision records (ADRs)

## License

MIT License - See [LICENSE](LICENSE) for details.