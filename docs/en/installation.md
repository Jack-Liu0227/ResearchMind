# Installation Guide

This guide will help you install and configure ResearchMind on your system.

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Python**: 3.9 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB available space
- **Network**: Internet connection for API access

### Recommended Requirements
- **Python**: 3.11 or higher
- **Memory**: 16GB RAM for large-scale simulations
- **Storage**: 10GB available space for data caching
- **GPU**: CUDA-compatible GPU for accelerated computations (optional)

## Installation Methods

### Method 1: Quick Install (Recommended)

```bash
# One-line clone and install
curl -fsSL https://raw.githubusercontent.com/your-org/researchmind/main/install.sh | bash
```

### Method 2: Manual Installation

#### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/researchmind.git
cd researchmind
```

#### Step 2: Create Virtual Environment

```bash
# Using venv (recommended)
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

#### Step 4: Install Google ADK

```bash
# Install Google ADK
pip install google-adk

# Verify installation
adk --version
```

### Method 3: Docker Installation

```bash
# Pull and run Docker container
docker pull researchmind/researchmind:latest
docker run -p 8080:8080 -v $(pwd)/data:/app/data researchmind/researchmind:latest
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Copy template
cp .env.example .env
```

Edit the `.env` file with your configuration:

```bash
# Required: Google API key for Gemini models
GOOGLE_API_KEY=your_google_api_key_here

# Optional: Materials Project API key
MATERIALS_PROJECT_API_KEY=your_mp_api_key_here

# Optional: MatterSim license
MATTERSIM_LICENSE=your_mattersim_license_here

# Optional: ArXiv API configuration
ARXIV_API_RATE_LIMIT=3
ARXIV_MAX_RESULTS=100

# Optional: Web search configuration
WEB_SEARCH_ENGINE=google
WEB_SEARCH_API_KEY=your_search_api_key

# Optional: Database configuration
DATABASE_URL=sqlite:///researchmind.db
CACHE_ENABLED=true
CACHE_TTL=3600

# Optional: Logging configuration
LOG_LEVEL=INFO
LOG_FILE=logs/researchmind.log
```

### API Key Setup

#### Google API Key (Required)
1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Add to `.env` file: `GOOGLE_API_KEY=your_key_here`

#### Materials Project API Key (Optional)
1. Register at [Materials Project](https://materialsproject.org/)
2. Generate API key in your profile
3. Add to `.env` file: `MATERIALS_PROJECT_API_KEY=your_key_here`

#### MatterSim License (Optional)
1. Contact [DeepModeling](https://deepmodeling.org/) for license
2. Add to `.env` file: `MATTERSIM_LICENSE=your_license_here`

### Agent Configuration

Edit `config/agent_config.yaml`:

```yaml
# Agent behavior settings
agents:
  coordinator:
    model: "gemini-2.0-flash"
    temperature: 0.1
    max_tokens: 4096
    
  literature:
    model: "gemini-2.0-flash"
    temperature: 0.2
    max_results: 20
    
  database:
    model: "gemini-2.0-flash"
    cache_enabled: true
    timeout: 30
    
  simulation:
    model: "gemini-2.0-flash"
    precision: "high"
    parallel_jobs: 4
    
  experiment:
    model: "gemini-2.0-flash"
    safety_checks: true
    cost_estimation: true

# Workflow settings
workflows:
  hybrid:
    decision_threshold: 0.7
    fallback_mode: "sequential"
    
  parallel:
    max_concurrent: 4
    timeout: 300
    
  sequential:
    early_stopping: true
    checkpoint_enabled: true
```

### MCP Server Configuration

Edit `config/mcp_config.yaml`:

```yaml
# MCP server settings
mcp_servers:
  literature:
    command: "python"
    args: ["mcp_servers/literature/server.py"]
    env:
      ARXIV_API_KEY: "${ARXIV_API_KEY}"
    timeout: 30
    
  materials:
    command: "python"
    args: ["mcp_servers/materials/server.py"]
    env:
      MATERIALS_PROJECT_API_KEY: "${MATERIALS_PROJECT_API_KEY}"
    timeout: 60
    
  simulation:
    command: "python"
    args: ["mcp_servers/simulation/server.py"]
    env:
      MATTERSIM_LICENSE: "${MATTERSIM_LICENSE}"
    timeout: 300
    
  experiment:
    command: "python"
    args: ["mcp_servers/experiment/server.py"]
    timeout: 30
```

## Verification

### Run System Tests

```bash
# Test all components
python test_agents.py

# Expected output:
# 🧪 Testing agent imports... ✅
# 🧪 Testing agent registry... ✅
# 🧪 Testing agent manager... ✅
# 🧪 Testing MCP servers... ✅
# 🧪 Testing configuration files... ✅
# 🧪 Testing workflow agents... ✅
# 🧪 Testing main program integration... ✅
# 📊 Test Results: 7/7 passed
# 🎉 All tests passed! ResearchMind is ready!
```

### Run Demo

```bash
# Run interactive demo
python main_mcp.py --demo

# Expected output:
# 🚀 ResearchMind Agent System Demo
# 🔍 === Literature Research Agent Demo ===
# 📋 Creating task: task_000001
# ✅ Task completed
# ...
```

### Test Individual Components

```bash
# Test literature agent
python main_mcp.py --agent literature_agent --research "test query"

# Test web interface
python main_mcp.py --web --port 8080
# Open http://localhost:8080 in browser
```

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Error: ModuleNotFoundError: No module named 'google.adk'
# Solution: Install Google ADK
pip install google-adk
```

#### API Key Issues
```bash
# Error: Invalid API key
# Solution: Check .env file and API key validity
cat .env | grep GOOGLE_API_KEY
```

#### MCP Server Startup Issues
```bash
# Error: MCP server failed to start
# Solution: Check server logs
python mcp_servers/literature/server.py --debug
```

#### Permission Issues (Linux/macOS)
```bash
# Error: Permission denied
# Solution: Make scripts executable
chmod +x scripts/*.sh
```

### Getting Help

If you encounter issues:

1. **Check logs**: `tail -f logs/researchmind.log`
2. **Run diagnostics**: `python test_agents.py --verbose`
3. **Check GitHub issues**: [Issues page](https://github.com/your-org/researchmind/issues)
4. **Ask for help**: [Discussions](https://github.com/your-org/researchmind/discussions)

### Performance Optimization

#### Improve Performance
```bash
# Enable caching
export CACHE_ENABLED=true

# Increase parallel jobs
export PARALLEL_JOBS=8

# Use faster models for development
export DEVELOPMENT_MODE=true
```

#### Production Settings
```bash
# Use production configuration
cp config/production.yaml config/agent_config.yaml

# Enable monitoring
export MONITORING_ENABLED=true
export LOG_LEVEL=WARNING
```

## Next Steps

After successful installation:

1. **Complete the [Quickstart](quickstart.md)** to create your first research workflow
2. **Explore [Agent Configuration](agent-config.md)** to customize behavior
3. **Try [Sample Projects](samples/)** to see ResearchMind in action
4. **Read [Best Practices](best-practices.md)** for optimal usage

---

**Installation Complete!** 🎉 You're ready to start using ResearchMind for intelligent research assistance.
