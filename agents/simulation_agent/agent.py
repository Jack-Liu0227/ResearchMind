"""
Simulation Agent using Google ADK framework with MCP tools.
"""
import os
from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from dotenv import load_dotenv

# Import modular prompt
from .prompts import SIMULATION_AGENT_INSTRUCTION

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# Create MCP toolset for simulation
toolset = MCPToolset(
    connection_params=SseServerParams(
        url=os.getenv('SIMULATION_MCP_URL', 'http://localhost:5003/sse'),
        timeout=180.0,  # Increased timeout for simulation tasks (3 minutes)
    ),
)

# Create root agent for simulation operations
root_agent = Agent(
    name="simulation_agent",
    model=LiteLlm(model=os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')),
    instruction=SIMULATION_AGENT_INSTRUCTION,  # Use modular prompt
    tools=[toolset]
)
