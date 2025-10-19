"""
深度研究智能体 - 简化为单一 Agent 架构

参考 database_agent 和 simulation_agent 的设计：
- 直接使用 MCPToolset
- 所有 paper_search 工具直接暴露给 Agent
- 避免复杂的子 agent 嵌套架构
- 使用 SSE 传输协议
"""
import os
from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# 导入 prompt
from .prompts import get_deep_research_instruction

# 创建 MCPToolset（使用 SSE 连接到 paper_search server）
toolset = MCPToolset(
    connection_params=SseServerParams(
        url=os.getenv('PAPER_SEARCH_MCP_URL', 'http://127.0.0.1:50004/sse'),
        timeout=180.0,  # Increased timeout for paper search and download (3 minutes)
    ),
)

# 创建 root agent（参考 database_agent 和 simulation_agent 的设计）
root_agent = Agent(
    name="deep_research_agent",
    model=LiteLlm(model=os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')),
    instruction=get_deep_research_instruction(),
    tools=[toolset]
)

