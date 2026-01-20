"""
Experiment Plan Agent using Google ADK framework.
"""
import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from dotenv import load_dotenv

# Import modular prompt
from .prompts import EXPERIMENT_PLAN_AGENT_INSTRUCTION

# Import callbacks
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.callbacks import trim_llm_request_context, record_llm_usage

# Import sub-agents to coordinate
from ..deep_research_agent.agent import root_agent as deep_research_agent
from ..database_agent.agent import root_agent as database_agent
from ..simulation_agent.agent import root_agent as simulation_agent

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# Create root agent for experimental planning and orchestration
root_agent = LlmAgent(
    name="experiment_plan_agent",
    model=LiteLlm(
        model=os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash'),
        api_key=os.getenv('OPENAI_API_KEY'),
        api_base=os.getenv('OPENAI_BASE_URL')
    ),
    instruction=EXPERIMENT_PLAN_AGENT_INSTRUCTION,
    tools=[
        AgentTool(agent=deep_research_agent),
        AgentTool(agent=database_agent),
        AgentTool(agent=simulation_agent),
    ],
    before_model_callback=trim_llm_request_context,
    after_model_callback=record_llm_usage
)
