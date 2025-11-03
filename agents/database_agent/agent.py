"""
Database Agent using Google ADK framework with MCP tools.
"""
import os
from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from dotenv import load_dotenv

# Import modular prompt
from .prompts import DATABASE_AGENT_INSTRUCTION

# Import callbacks
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from agents.callbacks import trim_llm_request_context, record_llm_usage

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# Create MCP toolset for materials database using SSE transport
toolset = MCPToolset(
    connection_params=SseServerParams(
        url=os.getenv('DATABASE_MCP_URL', 'http://127.0.0.1:50006/sse'),
        timeout=600.0,  # Increased timeout for AFLOW queries (10 minutes)
    ),
)

# Create root agent for database operations
root_agent = Agent(
    name="database_agent",
    model=LiteLlm(
        model=os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash'),
        api_key=os.getenv('OPENAI_API_KEY'),
        api_base=os.getenv('OPENAI_BASE_URL')
    ),
    instruction=DATABASE_AGENT_INSTRUCTION,
    tools=[toolset],
    before_model_callback=trim_llm_request_context,
    after_model_callback=record_llm_usage
)
