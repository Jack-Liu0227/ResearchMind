# Quickstart

Get ResearchMind up and running in under 10 minutes. This guide will walk you through creating your first intelligent research workflow.

## Prerequisites

- ResearchMind installed ([Installation Guide](installation.md))
- Google API key configured
- Basic familiarity with command line

## Your First Research Query

### 1. Interactive Mode

Start with interactive mode to get familiar with ResearchMind:

```bash
python main_mcp.py --interactive
```

You'll see a welcome message:
```
🧠 Welcome to ResearchMind - Intelligent Research Assistant!
Powered by Google ADK multi-agent system and MCP tool ecosystem
Type 'help' for assistance, 'quit' to exit
────────────────────────────────────────────────────────────

📝 Please enter your research query:
```

Try this example query:
```
Research high energy density lithium-ion battery cathode materials
```

### 2. What Happens Next

ResearchMind will automatically:

1. **🔍 Literature Search**: Find relevant papers on ArXiv and Google Scholar
2. **🗄️ Database Query**: Search Materials Project for cathode structures
3. **⚛️ Property Analysis**: Predict electrochemical properties
4. **🧪 Experiment Design**: Suggest synthesis protocols

You'll see real-time progress:
```
🤖 Agents are processing your request...
📊 Literature Agent: Found 15 relevant papers on Li-ion cathodes
📊 Database Agent: Retrieved 8 high-capacity cathode structures
📊 Simulation Agent: Calculated voltage profiles for top candidates
📊 Experiment Agent: Generated synthesis protocol for LiNi0.8Co0.1Mn0.1O2
✅ Processing complete!
```

## Understanding the Output

ResearchMind provides structured results:

### Literature Review Summary
```
📚 Literature Review Summary
────────────────────────────
• Found 15 papers (2020-2024)
• Key materials: NCM, NCA, LFP variants
• Trends: Single-crystal cathodes, coating strategies
• Performance metrics: 200-250 mAh/g capacity
```

### Materials Database Results
```
🗄️ Materials Database Results
────────────────────────────
• LiNi0.8Co0.1Mn0.1O2 (mp-1234567)
  - Theoretical capacity: 278 mAh/g
  - Average voltage: 3.8 V
  - Formation energy: -2.1 eV/atom
```

### Simulation Insights
```
⚛️ Simulation Predictions
────────────────────────────
• Electronic structure: Metallic behavior
• Li diffusion barrier: 0.3 eV
• Thermal stability: Stable to 300°C
```

### Experimental Protocol
```
🧪 Synthesis Protocol
────────────────────────────
• Method: Sol-gel synthesis
• Temperature: 850°C, 12 hours
• Atmosphere: Air
• Precursors: Li2CO3, Ni(NO3)2, Co(NO3)2, Mn(NO3)2
```

## Workflow Modes

### Hybrid Mode (Recommended)
Automatically selects the best strategy:

```bash
python main_mcp.py --research "perovskite solar cells" --workflow hybrid
```

**Best for**: Most research tasks, balancing speed and depth

### Sequential Mode
Step-by-step deep research:

```bash
python main_mcp.py --research "2D materials" --workflow sequential
```

**Best for**: Complex research requiring deep analysis

### Parallel Mode
Fast concurrent execution:

```bash
python main_mcp.py --research "catalyst screening" --workflow parallel
```

**Best for**: Rapid exploration and validation

## Specialized Agents

### Literature Research Expert

```bash
python main_mcp.py --agent literature_agent --research "machine learning in materials science"
```

**Capabilities**:
- ArXiv paper search with advanced filtering
- Google Scholar citation analysis
- Methodology extraction and comparison
- Trend analysis and research gap identification

### Database Search Expert

```bash
python main_mcp.py --agent database_agent --research "high entropy alloys"
```

**Capabilities**:
- Multi-database search (Materials Project, OQMD, NOMAD)
- AI structure generation using CrystaLLM
- Property prediction and validation
- 3D structure visualization

### Simulation Expert

```bash
python main_mcp.py --agent simulation_agent --research "electronic band structure"
```

**Capabilities**:
- MatterSim integration for accurate calculations
- Multi-scale modeling (atomic→materials→device)
- Property prediction (electronic, mechanical, thermal)
- Result analysis and visualization

### Experiment Designer

```bash
python main_mcp.py --agent experiment_agent --research "nanoparticle synthesis"
```

**Capabilities**:
- Design of Experiments (DOE) optimization
- Safety risk assessment
- Cost and time estimation
- Protocol generation for detailed procedures

## Advanced Usage

### Custom Research Workflows

Create targeted research queries:

```bash
# Focus on recent developments
python main_mcp.py --research "solid-state batteries published after 2023"

# Specific property requirements
python main_mcp.py --research "photovoltaic materials with bandgap 1-2 eV"

# Synthesis-oriented research
python main_mcp.py --research "scalable synthesis methods for graphene oxide"
```

### Web Interface

Get a visual experience:

```bash
python main_mcp.py --web --port 8080
```

Open http://localhost:8080 and:
1. Select the `research_coordinator` agent
2. Enter your research query
3. Watch real-time agent coordination
4. Export results in multiple formats

### Batch Processing

Process multiple queries:

```bash
# Create query file
echo "quantum dots for displays" > queries.txt
echo "thermoelectric materials" >> queries.txt
echo "superconducting materials" >> queries.txt

# Batch process
for query in $(cat queries.txt); do
    python main_mcp.py --research "$query" --workflow hybrid
done
```

## Tips for Better Results

### 1. Be Specific
❌ "Find materials"
✅ "Find lithium-ion battery cathode materials with capacity >200 mAh/g"

### 2. Include Context
❌ "Synthesis methods"
✅ "Scalable synthesis methods for perovskite solar cells for industrial production"

### 3. Specify Constraints
❌ "Design experiment"
✅ "Design low-cost experiment for graphene synthesis with budget <$1000"

### 4. Use Domain Keywords
Include relevant technical terms:
- "DFT calculations", "band structure", "formation energy"
- "sol-gel synthesis", "hydrothermal method", "CVD"
- "electrochemical performance", "cycling stability", "rate capability"

## Common Use Cases

### 1. Literature Review
```bash
python main_mcp.py --agent literature_agent --research "recent advances in solid-state electrolytes for lithium batteries"
```

### 2. Materials Discovery
```bash
python main_mcp.py --agent database_agent --research "novel 2D materials with direct bandgap"
```

### 3. Property Prediction
```bash
python main_mcp.py --agent simulation_agent --research "mechanical properties of high entropy alloys"
```

### 4. Experiment Planning
```bash
python main_mcp.py --agent experiment_agent --research "optimize synthesis conditions for single-crystal cathodes"
```

### 5. Comprehensive Research
```bash
python main_mcp.py --research "develop next-generation battery materials" --workflow hybrid
```

## Troubleshooting

### No Results Found
- Check spelling and technical terms
- Try broader or more specific queries
- Verify API keys are configured correctly

### Slow Performance
- Use parallel mode for faster results
- Check internet connection
- Consider using development mode for testing

### Error Messages
- Run `python test_agents.py` to diagnose issues
- Check logs at `logs/researchmind.log`
- Verify all dependencies are installed

## Next Steps

Now that you've completed the quickstart:

1. **Explore [Agent Configuration](agent-config.md)** to customize behavior
2. **Try [Sample Projects](samples/)** for domain-specific examples
3. **Learn [Workflow Patterns](workflow-patterns.md)** for advanced orchestration
4. **Read [Best Practices](best-practices.md)** for optimal usage

## Getting Help

- **Documentation**: Browse the complete [documentation](README.md)
- **Examples**: Check out [sample projects](samples/)
- **Community**: Join [discussions](https://github.com/your-org/researchmind/discussions)
- **Issues**: Report bugs on [GitHub](https://github.com/your-org/researchmind/issues)

---

**Congratulations!** 🎉 You've successfully created your first intelligent research workflow with ResearchMind. Ready to dive deeper? Explore our [advanced tutorials](tutorials/) next.
