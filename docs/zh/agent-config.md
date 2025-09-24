# 智能体配置

学习如何配置和定制ResearchMind智能体以满足您的特定研究需求。

> 🇺🇸 **English Users**: [Click here for English version](../agent-config.md) | **英文用户**: [点击这里查看英文版本](../agent-config.md)

## 概述

ResearchMind使用分层多智能体系统，每个智能体都可以针对不同研究领域进行个性化配置以获得最佳性能。

## 智能体层次结构

### 根协调器
主要的编排智能体，管理所有子智能体和工作流：

```yaml
# config/agent_config.yaml
agents:
  coordinator:
    name: "research_coordinator"
    model: "gemini-2.0-flash"
    temperature: 0.1
    max_tokens: 4096
    instruction: |
      您是ResearchMind的主协调器。您的任务是：
      1. 理解用户的研究需求
      2. 选择合适的专业智能体
      3. 协调多智能体工作流
      4. 整合和呈现最终结果
    
    # 可用的子智能体
    sub_agents:
      - literature_agent
      - database_agent
      - simulation_agent
      - experiment_agent
      - workflow_agent
```

### 专业智能体

#### 文献研究智能体
```yaml
  literature:
    name: "literature_agent"
    model: "gemini-2.0-flash"
    temperature: 0.2
    max_tokens: 3072
    instruction: |
      您是文献研究专家。专门从事：
      - ArXiv论文搜索和分析
      - Google Scholar引用分析
      - 研究趋势识别
      - 方法论比较
      - 文献综述生成
    
    # 工具配置
    tools:
      - search_arxiv
      - search_scholar
      - search_web
      - analyze_paper
      - generate_report
    
    # 搜索参数
    search_config:
      max_results: 20
      date_range: "2020-2024"
      quality_threshold: 0.7
```

#### 数据库智能体
```yaml
  database:
    name: "database_agent"
    model: "gemini-2.0-flash"
    temperature: 0.1
    max_tokens: 3072
    instruction: |
      您是材料数据库专家。专门从事：
      - Materials Project数据库查询
      - 结构搜索和筛选
      - 性质预测和验证
      - 结构生成和优化
      - 数据可视化
    
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

#### 仿真智能体
```yaml
  simulation:
    name: "simulation_agent"
    model: "gemini-2.0-flash"
    temperature: 0.1
    max_tokens: 4096
    instruction: |
      您是计算仿真专家。专门从事：
      - MatterSim计算设置
      - 电子结构计算
      - 性质预测和分析
      - 结构优化
      - 结果解释和可视化
    
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

#### 实验设计智能体
```yaml
  experiment:
    name: "experiment_agent"
    model: "gemini-2.0-flash"
    temperature: 0.2
    max_tokens: 3072
    instruction: |
      您是实验设计专家。专门从事：
      - 实验协议设计
      - 参数优化（DOE）
      - 安全风险评估
      - 成本效益分析
      - 程序生成
    
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

## 工作流配置

### 混合工作流
```yaml
workflows:
  hybrid:
    name: "hybrid_workflow"
    description: "智能选择最佳策略"
    decision_threshold: 0.7
    fallback_mode: "sequential"
    
    # 决策规则
    decision_rules:
      - condition: "task_complexity < 0.3"
        action: "parallel"
      - condition: "task_complexity > 0.7"
        action: "sequential"
      - condition: "time_constraint == 'urgent'"
        action: "parallel"
      - default: "sequential"
```

### 顺序工作流
```yaml
  sequential:
    name: "sequential_workflow"
    description: "逐步深度研究"
    early_stopping: true
    checkpoint_enabled: true
    
    # 执行顺序
    execution_order:
      - literature_agent
      - database_agent
      - simulation_agent
      - experiment_agent
    
    # 停止条件
    stopping_conditions:
      - "confidence_score > 0.9"
      - "time_elapsed > 1800"  # 30分钟
```

### 并行工作流
```yaml
  parallel:
    name: "parallel_workflow"
    description: "快速并发执行"
    max_concurrent: 4
    timeout: 300
    
    # 并行组
    parallel_groups:
      - [literature_agent, database_agent]
      - [simulation_agent, experiment_agent]
```

## 模型配置

### 模型选择策略
```yaml
model_config:
  # 生产环境
  production:
    primary: "gemini-2.0-flash"
    fallback: "gemini-1.5-pro"
    
  # 开发环境
  development:
    primary: "gemini-1.5-flash"
    fallback: "gemini-1.0-pro"
    
  # 成本优化
  cost_optimized:
    primary: "gemini-1.5-flash"
    fallback: "gemini-1.0-pro"
```

### 性能调优
```yaml
performance:
  # 温度设置
  temperature:
    creative_tasks: 0.3      # 实验设计、假设生成
    analytical_tasks: 0.1    # 数据分析、计算
    search_tasks: 0.2        # 文献搜索、数据库查询
    
  # 令牌限制
  max_tokens:
    simple_queries: 1024
    complex_analysis: 4096
    comprehensive_reports: 8192
    
  # 超时设置
  timeouts:
    quick_search: 30
    detailed_analysis: 120
    complex_simulation: 600
```

## 环境特定配置

### 开发环境
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
  rate_limit: 10  # 每分钟请求数
  retry_attempts: 3
```

### 生产环境
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

## 自定义智能体

### 创建领域专用智能体
```yaml
# 示例：催化剂研究智能体
agents:
  catalyst_agent:
    name: "catalyst_research_agent"
    model: "gemini-2.0-flash"
    temperature: 0.15
    max_tokens: 3072
    
    instruction: |
      您是催化剂研究专家。专门从事：
      - 催化剂设计和筛选
      - 反应机理分析
      - 活性位点识别
      - 载体选择和优化
      - 反应条件优化
    
    # 专用工具
    tools:
      - search_catalyst_database
      - predict_activity
      - analyze_mechanism
      - optimize_support
      - design_reactor
    
    # 领域知识
    domain_knowledge:
      reaction_types: ["hydrogenation", "oxidation", "coupling"]
      catalyst_types: ["heterogeneous", "homogeneous", "enzymatic"]
      characterization: ["XRD", "XPS", "TEM", "BET", "TPR"]
```

### 智能体注册
```python
# agents/custom_agents.py
from google.adk.agents import LlmAgent
from agents.agent_manager import AgentManager

def register_catalyst_agent():
    """注册催化剂研究智能体"""
    catalyst_agent = LlmAgent(
        name="catalyst_research_agent",
        model="gemini-2.0-flash",
        instruction="""您是催化剂研究专家...""",
        tools=get_catalyst_tools()
    )
    
    # 注册到管理器
    manager = AgentManager()
    manager.register_agent(catalyst_agent)
    
    return catalyst_agent
```

## 配置最佳实践

### 1. 性能优化
- 根据任务复杂度选择合适的模型
- 设置合理的超时和重试机制
- 启用缓存以减少重复计算

### 2. 成本控制
- 使用成本效益高的模型进行开发
- 设置令牌限制和速率限制
- 监控API使用情况

### 3. 可靠性
- 配置故障转移和回退机制
- 启用断路器模式
- 实施健康检查

### 4. 安全性
- 使用环境变量管理敏感信息
- 实施访问控制和审计
- 定期轮换API密钥

## 故障排除

### 常见配置问题

#### 智能体无响应
```yaml
# 检查超时设置
agents:
  coordinator:
    timeout: 120  # 增加超时时间
    retry_attempts: 3
```

#### 性能缓慢
```yaml
# 优化并发设置
workflows:
  parallel:
    max_concurrent: 8  # 增加并发数
    batch_size: 4
```

#### 成本过高
```yaml
# 使用成本优化配置
model_config:
  cost_optimized: true
  max_tokens: 2048  # 减少令牌限制
```

## 配置验证

### 验证配置文件
```bash
# 验证YAML语法
python -c "import yaml; yaml.safe_load(open('config/agent_config.yaml'))"

# 测试智能体配置
python test_agents.py --config-only

# 验证工具连接
python test_agents.py --tools-only
```

### 配置模板
```bash
# 生成配置模板
python scripts/generate_config.py --template agent_config

# 验证配置完整性
python scripts/validate_config.py config/agent_config.yaml
```

---

通过合理的配置，您可以优化ResearchMind智能体的性能，满足特定的研究需求，并确保系统的可靠性和成本效益。
