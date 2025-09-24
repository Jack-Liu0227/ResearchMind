# Agent Configuration

Learn how to configure and customize ResearchMind agents for your specific research needs.

## Overview

ResearchMind uses a hierarchical multi-agent system where each agent can be individually configured for optimal performance in different research domains.

## Agent Hierarchy

### Root Coordinator
The main orchestration agent that manages all sub-agents and workflows:

```yaml
# config/agent_config.yaml
agents:
  coordinator:
    name: "research_coordinator"
    model: "gemini-2.0-flash"
    temperature: 0.1
    max_tokens: 4096
    instruction: |
      You are the main coordinator for ResearchMind. Your tasks are to:
      1. Understand user research requirements
      2. Select appropriate specialized agents
      3. Coordinate multi-agent workflows
      4. Integrate and present final results
    
    # Available sub-agents
    sub_agents:
      - literature_agent
      - database_agent
      - simulation_agent
      - experiment_agent
      - workflow_agent
```

### Specialized Agents

#### Literature Research Agent
```yaml
  literature:
    name: "literature_agent"
    model: "gemini-2.0-flash"
    temperature: 0.2
    max_tokens: 3072
    instruction: |
      You are a literature research expert. You specialize in:
      - ArXiv paper search and analysis
      - Google Scholar citation analysis
      - Research trend identification
      - Methodology comparison
      - Literature review generation
    
    # Tool configuration
    tools:
      - search_arxiv
      - search_scholar
      - search_web
      - analyze_paper
      - generate_report
    
    # Search parameters
    search_config:
      max_results: 20
      date_range: "2020-2024"
      quality_threshold: 0.7
```

#### Database Agent
```yaml
  database:
    name: "database_agent"
    model: "gemini-2.0-flash"
    temperature: 0.1
    max_tokens: 3072
    instruction: |
      You are a materials database expert. You specialize in:
      - Materials Project database queries
      - Structure search and filtering
      - Property prediction and validation
      - Structure generation and optimization
      - Data visualization
    
    tools:
      - search_structure
      - generate_structure
      - predict_properties
      - validate_structure
      - visualize_structure
    
    database_config:
      cache_enabled: true
      timeout: 30
      max_structures: 50
```

#### Simulation Agent
```yaml
  simulation:
    name: "simulation_agent"
    model: "gemini-2.0-flash"
    temperature: 0.1
    max_tokens: 4096
    instruction: |
      You are a computational simulation expert. You specialize in:
      - MatterSim calculation setup
      - Electronic structure calculations
      - Property prediction and analysis
      - Structure optimization
      - Result interpretation and visualization
    
    tools:
      - setup_calculation
      - run_mattersim
      - analyze_results
      - optimize_structure
      - calculate_properties
    
    simulation_config:
      precision: "high"
      parallel_jobs: 4
      timeout: 300
```

#### Experiment Agent
```yaml
  experiment:
    name: "experiment_agent"
    model: "gemini-2.0-flash"
    temperature: 0.2
    max_tokens: 3072
    instruction: |
      You are an experimental design expert. You specialize in:
      - Experimental protocol design
      - Parameter optimization (DOE)
      - Safety risk assessment
      - Cost-benefit analysis
      - Procedure generation
    
    tools:
      - design_experiment
      - optimize_parameters
      - assess_risk
      - generate_protocol
      - estimate_cost
    
    experiment_config:
      safety_checks: true
      cost_estimation: true
      doe_methods: ["factorial", "response_surface", "bayesian"]
```

## Workflow Configuration

### Hybrid Workflow
```yaml
workflows:
  hybrid:
    name: "hybrid_workflow"
    description: "Intelligently selects optimal strategy"
    decision_threshold: 0.7
    fallback_mode: "sequential"
    
    # Decision rules
    decision_rules:
      - condition: "task_complexity < 0.3"
        action: "parallel"
      - condition: "task_complexity > 0.7"
        action: "sequential"
      - condition: "time_constraint == 'urgent'"
        action: "parallel"
      - default: "sequential"
```

### Sequential Workflow
```yaml
  sequential:
    name: "sequential_workflow"
    description: "Step-by-step deep research"
    early_stopping: true
    checkpoint_enabled: true
    
    # Execution order
    execution_order:
      - literature_agent
      - database_agent
      - simulation_agent
      - experiment_agent
    
    # Stopping conditions
    stopping_conditions:
      - "confidence_score > 0.9"
      - "time_elapsed > 1800"  # 30 minutes
```

### Parallel Workflow
```yaml
  parallel:
    name: "parallel_workflow"
    description: "Fast concurrent execution"
    max_concurrent: 4
    timeout: 300
    
    # Parallel groups
    parallel_groups:
      - [literature_agent, database_agent]
      - [simulation_agent, experiment_agent]
```

## Model Configuration

### Model Selection Strategy
```yaml
model_config:
  # Production environment
  production:
    primary: "gemini-2.0-flash"
    fallback: "gemini-1.5-pro"
    
  # Development environment
  development:
    primary: "gemini-1.5-flash"
    fallback: "gemini-1.0-pro"
    
  # Cost optimized
  cost_optimized:
    primary: "gemini-1.5-flash"
    fallback: "gemini-1.0-pro"
```

### Performance Tuning
```yaml
performance:
  # Temperature settings
  temperature:
    creative_tasks: 0.3      # Experiment design, hypothesis generation
    analytical_tasks: 0.1    # Data analysis, calculations
    search_tasks: 0.2        # Literature search, database queries
    
  # Token limits
  max_tokens:
    simple_queries: 1024
    complex_analysis: 4096
    comprehensive_reports: 8192
    
  # Timeout settings
  timeouts:
    quick_search: 30
    detailed_analysis: 120
    complex_simulation: 600
```

## Environment-Specific Configuration

### Development Environment
```yaml
# config/development.yaml
environment: "development"
debug_mode: true
log_level: "DEBUG"
cache_enabled: true

agents:
  coordinator:
    model: "gemini-1.5-flash"
    temperature: 0.2
    
model_config:
  rate_limit: 10  # requests per minute
  retry_attempts: 3
```

### Production Environment
```yaml
# config/production.yaml
environment: "production"
debug_mode: false
log_level: "INFO"
monitoring_enabled: true

agents:
  coordinator:
    model: "gemini-2.0-flash"
    temperature: 0.1
    
model_config:
  rate_limit: 60
  retry_attempts: 5
  circuit_breaker: true
```

## Custom Agents

### Creating Domain-Specific Agents
```yaml
# Example: Catalyst research agent
agents:
  catalyst_agent:
    name: "catalyst_research_agent"
    model: "gemini-2.0-flash"
    temperature: 0.15
    max_tokens: 3072
    
    instruction: |
      You are a catalyst research expert. You specialize in:
      - Catalyst design and screening
      - Reaction mechanism analysis
      - Active site identification
      - Support selection and optimization
      - Reaction condition optimization
    
    # Specialized tools
    tools:
      - search_catalyst_database
      - predict_activity
      - analyze_mechanism
      - optimize_support
      - design_reactor
    
    # Domain knowledge
    domain_knowledge:
      reaction_types: ["hydrogenation", "oxidation", "coupling"]
      catalyst_types: ["heterogeneous", "homogeneous", "enzymatic"]
      characterization: ["XRD", "XPS", "TEM", "BET", "TPR"]
```

### Agent Registration
```python
# agents/custom_agents.py
from google.adk.agents import LlmAgent
from agents.agent_manager import AgentManager

def register_catalyst_agent():
    """Register catalyst research agent"""
    catalyst_agent = LlmAgent(
        name="catalyst_research_agent",
        model="gemini-2.0-flash",
        instruction="""You are a catalyst research expert...""",
        tools=get_catalyst_tools()
    )
    
    # Register with manager
    manager = AgentManager()
    manager.register_agent(catalyst_agent)
    
    return catalyst_agent
```

## Configuration Best Practices

### 1. Performance Optimization
- Choose appropriate models based on task complexity
- Set reasonable timeouts and retry mechanisms
- Enable caching to reduce redundant computations

### 2. Cost Control
- Use cost-effective models for development
- Set token limits and rate limits
- Monitor API usage

### 3. Reliability
- Configure fallback and retry mechanisms
- Enable circuit breaker patterns
- Implement health checks

### 4. Security
- Use environment variables for sensitive information
- Implement access controls and auditing
- Regularly rotate API keys

## Troubleshooting

### Common Configuration Issues

#### Agent Not Responding
```yaml
# Check timeout settings
agents:
  coordinator:
    timeout: 120  # Increase timeout
    retry_attempts: 3
```

#### Slow Performance
```yaml
# Optimize concurrency settings
workflows:
  parallel:
    max_concurrent: 8  # Increase concurrency
    batch_size: 4
```

#### High Costs
```yaml
# Use cost optimization
model_config:
  cost_optimized: true
  max_tokens: 2048  # Reduce token limits
```

## Configuration Validation

### Validate Configuration Files
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/agent_config.yaml'))"

# Test agent configuration
python test_agents.py --config-only

# Validate tool connections
python test_agents.py --tools-only
```

### Configuration Templates
```bash
# Generate configuration template
python scripts/generate_config.py --template agent_config

# Validate configuration completeness
python scripts/validate_config.py config/agent_config.yaml
```

---

Through proper configuration, you can optimize ResearchMind agents for your specific research needs while ensuring reliability and cost-effectiveness.
