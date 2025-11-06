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

"""ResearchMind: Multi-agent system for materials science research."""

import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from .prompt import RESEARCH_COORDINATOR_PROMPT
from .callbacks import trim_llm_request_context, record_llm_usage

# Import sub-agents
from .deep_research_agent.agent import root_agent as deep_research_agent
from .database_agent.agent import root_agent as database_agent
from .simulation_agent.agent import root_agent as simulation_agent

# Get model from environment
MODEL = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')

# Create the main coordinator agent
research_coordinator = LlmAgent(
    name="research_coordinator",
    model=LiteLlm(
        model=MODEL,
        api_key=os.getenv('OPENAI_API_KEY'),
        api_base=os.getenv('OPENAI_BASE_URL')
    ),
    description=(
        "Coordinating materials science research by analyzing user queries, "
        "delegating to specialized sub-agents (literature, database, simulation), "
        "and providing comprehensive research assistance"
    ),
    instruction=RESEARCH_COORDINATOR_PROMPT,
    output_key="research_query",
    tools=[
        AgentTool(agent=deep_research_agent),
        AgentTool(agent=database_agent),
        AgentTool(agent=simulation_agent),
    ],
    before_model_callback=trim_llm_request_context,
    after_model_callback=record_llm_usage
)

# Export the main agent as root_agent for compatibility
root_agent = research_coordinator


