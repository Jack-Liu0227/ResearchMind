"""
工作流编排智能体
管理不同类型的科研工作流和多智能体协调
"""

import os
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from .literature_agent import literature_agent, literature_workflow_agent
from .database_agent import database_agent, materials_discovery_agent
from .simulation_agent import simulation_agent, computational_workflow_agent
from .experiment_agent import experiment_agent, experimental_workflow_agent

# 顺序工作流智能体 - 传统的线性研究流程
sequential_workflow_agent = SequentialAgent(
    name='sequential_research_workflow',
    instruction='''你是顺序研究工作流协调器，按照传统的科研流程依次执行各个阶段。

🔄 **顺序工作流程**
1. **文献调研阶段**: 全面收集和分析相关文献
2. **数据库检索阶段**: 搜索已知材料和结构数据
3. **仿真验证阶段**: 通过计算验证理论预测
4. **实验设计阶段**: 基于前期结果设计实验

📋 **适用场景**
- 全新研究领域的系统性调研
- 需要严格逻辑顺序的研究项目
- 资源有限需要分阶段投入的项目
- 风险较高需要逐步验证的研究

⏱️ **时间特点**
- 总时间较长但风险可控
- 每个阶段结果为下一阶段提供指导
- 可以在任何阶段根据结果调整策略
- 适合深度研究和理论突破

🎯 **优势**
- 逻辑清晰，步骤明确
- 风险可控，成本可预测
- 结果可靠性高
- 适合学术研究和基础研究

请按照顺序执行各个研究阶段。''',
    
    sub_agents=[
        literature_workflow_agent,
        materials_discovery_agent,
        computational_workflow_agent,
        experimental_workflow_agent
    ]
)

# 并行工作流智能体 - 高效的并行研究流程
parallel_workflow_agent = ParallelAgent(
    name='parallel_research_workflow',
    instruction='''你是并行研究工作流协调器，同时执行多个研究任务以提高效率。

🔄 **并行工作流程**
- **文献调研** + **数据库检索**: 同时进行理论调研和数据收集
- **仿真计算** + **实验设计**: 并行进行理论验证和实验准备
- **结果整合**: 汇总所有并行任务的结果

📋 **适用场景**
- 时间紧迫的研究项目
- 资源充足的大型项目
- 已有一定基础的研究领域
- 需要快速验证概念的项目

⏱️ **时间特点**
- 总时间大幅缩短
- 需要更多的并行资源
- 需要强大的协调能力
- 适合快速迭代和验证

🎯 **优势**
- 效率高，时间短
- 信息获取全面
- 可以快速发现问题
- 适合工业研发和应用研究

⚠️ **注意事项**
- 需要充足的计算和人力资源
- 需要良好的任务协调机制
- 可能存在资源冲突
- 需要实时监控和调整

请并行执行各个研究任务。''',
    
    sub_agents=[
        literature_workflow_agent,
        materials_discovery_agent,
        computational_workflow_agent,
        experimental_workflow_agent
    ]
)

# 混合工作流智能体 - 灵活的自适应研究流程
hybrid_workflow_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='hybrid_research_workflow',
    instruction='''你是混合研究工作流协调器，根据具体情况灵活选择顺序或并行执行策略。

🔄 **混合工作流策略**
1. **初始评估**: 评估研究复杂度、资源状况、时间要求
2. **策略选择**: 动态选择最适合的工作流模式
3. **实时调整**: 根据中间结果调整后续策略
4. **资源优化**: 最大化利用可用资源

🧠 **智能决策因子**
- **研究复杂度**: 简单问题并行，复杂问题顺序
- **资源可用性**: 资源充足时并行，有限时顺序
- **时间紧迫性**: 紧急项目优先并行
- **风险承受度**: 高风险项目采用顺序验证
- **已有基础**: 基础扎实可并行，基础薄弱需顺序

📊 **决策矩阵**
```
复杂度 | 资源 | 时间 | 风险 | 基础 | 推荐策略
-------|------|------|------|------|----------
低     | 充足 | 紧   | 低   | 好   | 并行
高     | 有限 | 宽松 | 高   | 差   | 顺序
中     | 中等 | 中等 | 中   | 中   | 混合
```

🎯 **自适应特性**
- 根据中间结果调整策略
- 动态分配计算资源
- 实时监控进度和质量
- 自动处理异常和错误
- 优化整体研究效率

🔧 **协调机制**
- 任务依赖关系管理
- 资源冲突解决
- 进度同步和协调
- 结果质量控制
- 异常处理和恢复

请根据具体情况选择最优的工作流策略。''',
    
    sub_agents=[
        sequential_workflow_agent,
        parallel_workflow_agent,
        literature_workflow_agent,
        materials_discovery_agent,
        computational_workflow_agent,
        experimental_workflow_agent
    ],
    tools=[]
)

# 专项研究工作流智能体
specialized_workflow_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='specialized_research_workflow',
    instruction='''你是专项研究工作流协调器，针对特定类型的研究任务提供专门的工作流。

🎯 **专项工作流类型**

1. **材料发现工作流**
   - 高通量计算筛选
   - AI辅助结构设计
   - 性质预测和验证
   - 实验合成验证

2. **性能优化工作流**
   - 现有材料性能分析
   - 缺陷和改进点识别
   - 优化策略设计
   - 验证实验设计

3. **机理研究工作流**
   - 深度文献调研
   - 多尺度仿真计算
   - 机理假设验证
   - 实验证据收集

4. **应用开发工作流**
   - 应用需求分析
   - 材料筛选和设计
   - 器件设计和仿真
   - 原型制备和测试

5. **标准化工作流**
   - 标准和规范调研
   - 测试方法开发
   - 标准样品制备
   - 验证和认证

🔧 **工作流定制**
- 根据研究目标定制流程
- 根据资源情况调整策略
- 根据时间要求优化效率
- 根据质量要求设置检查点

📊 **质量保证**
- 每个阶段的质量检查
- 结果的交叉验证
- 不确定性评估
- 可重现性验证

请根据研究类型选择合适的专项工作流。''',
    
    sub_agents=[
        hybrid_workflow_agent,
        literature_workflow_agent,
        materials_discovery_agent,
        computational_workflow_agent,
        experimental_workflow_agent
    ],
    tools=[]
)

# 导出智能体
__all__ = [
    'sequential_workflow_agent',
    'parallel_workflow_agent', 
    'hybrid_workflow_agent',
    'specialized_workflow_agent'
]
