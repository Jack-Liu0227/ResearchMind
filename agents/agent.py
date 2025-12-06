# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ResearchMind: Multi-agent system for materials science research.

架构说明：
- 主协调器：LlmAgent（支持多轮对话和工具调用）
- 子 Agent 集成：通过 AgentTool 包装三个专业 Agent
  1. deep_research_agent: 文献搜索与分析（MCP: paper_search, 端口 50004）
  2. database_agent: 材料数据库查询（MCP: database, 端口 50006）
  3. simulation_agent: 仿真计算（MCP: simulation, 端口 50005）
- 接口兼容性：所有子 Agent 都导出 root_agent（Agent 类型）
- 共享 callbacks：trim_llm_request_context（上下文修剪）、record_llm_usage（使用记录）
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from .prompt import RESEARCH_COORDINATOR_PROMPT
from .callbacks import trim_llm_request_context, record_llm_usage

# 导入子 Agent（所有子 Agent 都导出 root_agent）
from .deep_research_agent.agent import root_agent as deep_research_agent
from .database_agent.agent import root_agent as database_agent
from .simulation_agent.agent import root_agent as simulation_agent

# 从环境变量获取模型配置
MODEL = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')

# 创建主研究协调 Agent
research_coordinator = LlmAgent(
    name="research_coordinator",
    model=LiteLlm(
        model=MODEL,
        api_key=os.getenv('OPENAI_API_KEY'),
        api_base=os.getenv('OPENAI_BASE_URL')
    ),
    description=(
        "协调材料科学研究：分析用户查询，分发任务给专业子 Agent "
        "（文献、数据库、仿真），提供综合研究支持"
    ),
    instruction=RESEARCH_COORDINATOR_PROMPT,
    output_key="research_query",
    tools=[
        # 使用 AgentTool 包装子 Agent，使其可作为工具调用
        AgentTool(agent=deep_research_agent),
        AgentTool(agent=database_agent),
        AgentTool(agent=simulation_agent),
    ],
    before_model_callback=trim_llm_request_context,  # 防止上下文超过 token 限制
    after_model_callback=record_llm_usage  # 记录 LLM 使用情况并计费
)

# 导出主 Agent 以保持兼容性
root_agent = research_coordinator


