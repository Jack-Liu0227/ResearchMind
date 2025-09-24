#!/usr/bin/env python3
"""
ResearchMind - 智能科研助手主程序 (MCP架构版本)
基于Google ADK多智能体架构和MCP工具生态的科研辅助系统
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from google.adk.agents import LlmAgent
from google.adk.agents.workflow_agents import SequentialAgent, ParallelAgent, LoopAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams, SseConnectionParams
from mcp import StdioServerParameters

# 导入ResearchMind智能体
from agents import (
    root_agent,
    literature_agent,
    database_agent,
    simulation_agent,
    experiment_agent,
    sequential_workflow_agent,
    parallel_workflow_agent,
    hybrid_workflow_agent,
    agent_manager
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_cli() -> argparse.ArgumentParser:
    """设置命令行界面"""
    parser = argparse.ArgumentParser(
        description="ResearchMind - 智能科研助手 (基于Google ADK + MCP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 使用示例:
  python main_mcp.py --interactive                    # 交互式模式
  python main_mcp.py --research "新能源材料"           # 直接研究模式
  python main_mcp.py --workflow hybrid               # 智能混合工作流
  python main_mcp.py --workflow sequential           # 顺序工作流
  python main_mcp.py --workflow parallel             # 并行工作流
  python main_mcp.py --agent literature_agent        # 使用文献调研专家
  python main_mcp.py --demo                          # 运行智能体演示
  python main_mcp.py --web --port 8080               # 启动ADK Web界面
  python main_mcp.py --deploy cloud_run              # 部署到Cloud Run
        """
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="启动交互式模式"
    )
    
    parser.add_argument(
        "--research", "-r",
        type=str,
        help="直接指定研究主题"
    )
    
    parser.add_argument(
        "--workflow", "-w",
        choices=["sequential", "parallel", "hybrid", "specialized"],
        default="hybrid",
        help="选择工作流模式"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config/mcp_config.yaml",
        help="MCP配置文件路径"
    )
    
    parser.add_argument(
        "--web",
        action="store_true",
        help="启动ADK Web界面"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="Web服务器端口"
    )
    
    parser.add_argument(
        "--deploy",
        choices=["cloud_run", "gke", "vertex_ai"],
        help="部署到云平台"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="启用调试模式"
    )

    parser.add_argument(
        "--agent", "-a",
        type=str,
        help="指定使用的智能体名称"
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="运行智能体演示"
    )

    return parser

async def create_mcp_agents():
    """创建基于MCP的智能体"""
    
    # 文献调研智能体
    literature_agent = LlmAgent(
        model='gemini-2.0-flash',
        name='literature_researcher',
        instruction='''你是专业的文献调研专家。能够：
        1. 搜索ArXiv、Google Scholar等数据库
        2. 分析论文内容和研究方法
        3. 生成结构化的文献调研报告
        4. 提取可行的研究方案''',
        tools=[
            MCPToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command='python',
                        args=['mcp_servers/literature/server.py'],
                    ),
                ),
                tool_filter=['search_arxiv', 'search_scholar', 'analyze_paper', 'generate_report']
            )
        ],
    )
    
    # 材料数据库智能体
    database_agent = LlmAgent(
        model='gemini-2.0-flash',
        name='database_specialist',
        instruction='''你是材料数据库检索专家。能够：
        1. 搜索Materials Project、OQMD等数据库
        2. 查找和分析晶体结构
        3. 使用CrystaLLM生成新结构
        4. 预测材料性质''',
        tools=[
            MCPToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command='python',
                        args=['mcp_servers/materials/server.py'],
                    ),
                ),
                tool_filter=['search_structure', 'generate_structure', 'predict_properties']
            )
        ],
    )
    
    # 仿真计算智能体
    simulation_agent = LlmAgent(
        model='gemini-2.0-flash',
        name='simulation_expert',
        instruction='''你是多尺度仿真建模专家。能够：
        1. 使用MatterSim进行原子级计算
        2. 设置和优化计算参数
        3. 分析仿真结果
        4. 可视化结构和性质''',
        tools=[
            MCPToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command='python',
                        args=['mcp_servers/simulation/server.py'],
                        env={'MATTERSIM_LICENSE': os.getenv('MATTERSIM_LICENSE', '')}
                    ),
                ),
                tool_filter=['setup_calculation', 'run_mattersim', 'analyze_results']
            )
        ],
    )
    
    # 实验设计智能体
    experiment_agent = LlmAgent(
        model='gemini-2.0-flash',
        name='experiment_designer',
        instruction='''你是实验设计和优化专家。能够：
        1. 基于文献和仿真结果设计实验
        2. 优化实验参数
        3. 评估实验风险和可行性
        4. 生成详细的实验协议''',
        tools=[
            MCPToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command='python',
                        args=['mcp_servers/experiment/server.py'],
                    ),
                ),
                tool_filter=['design_experiment', 'optimize_parameters', 'assess_risk']
            )
        ],
    )
    
    return literature_agent, database_agent, simulation_agent, experiment_agent

async def create_workflow_agent(workflow_type: str):
    """创建工作流智能体"""
    literature_agent, database_agent, simulation_agent, experiment_agent = await create_mcp_agents()
    
    if workflow_type == "sequential":
        # 顺序工作流：文献调研 → 数据库检索 → 仿真验证 → 实验设计
        return SequentialAgent(
            name="research_pipeline",
            instruction="按顺序执行科研流程：文献调研、数据库检索、仿真验证、实验设计",
            agents=[literature_agent, database_agent, simulation_agent, experiment_agent]
        )
    
    elif workflow_type == "parallel":
        # 并行工作流：同时进行文献调研、数据库检索、仿真计算，最后汇总到实验设计
        return ParallelAgent(
            name="parallel_research",
            instruction="并行执行文献调研、数据库检索和仿真计算，然后汇总结果进行实验设计",
            agents=[literature_agent, database_agent, simulation_agent],
            gather_agent=experiment_agent
        )
    
    else:  # iterative
        # 迭代工作流：根据结果反馈进行迭代优化
        return LoopAgent(
            name="iterative_research",
            instruction="迭代优化研究方案，根据仿真结果调整实验设计",
            agent=SequentialAgent(
                name="research_iteration",
                agents=[literature_agent, database_agent, simulation_agent, experiment_agent]
            ),
            max_iterations=3
        )

async def get_coordinator_agent(workflow_type: str = "hybrid", agent_name: str = None):
    """获取协调器智能体"""

    # 如果指定了特定智能体，直接返回
    if agent_name:
        from agents import get_agent
        agent = get_agent(agent_name)
        if agent:
            return agent
        else:
            logger.warning(f"未找到智能体 {agent_name}，使用默认协调器")

    # 根据工作流类型选择智能体
    if workflow_type == "sequential":
        from agents import sequential_workflow_agent
        return sequential_workflow_agent
    elif workflow_type == "parallel":
        from agents import parallel_workflow_agent
        return parallel_workflow_agent
    elif workflow_type == "specialized":
        from agents import specialized_workflow_agent
        return specialized_workflow_agent
    else:  # hybrid (default)
        from agents import root_agent
        return root_agent

async def interactive_mode(coordinator_agent: LlmAgent):
    """交互式模式"""
    print("🧠 欢迎使用 ResearchMind - 智能科研助手 (MCP架构)!")
    print("基于Google ADK多智能体系统和MCP工具生态")
    print("输入 'help' 查看帮助，输入 'quit' 退出")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\n📝 请输入您的研究需求: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 感谢使用 ResearchMind!")
                break
            elif user_input.lower() == 'help':
                print_help()
                continue
            elif not user_input:
                continue
            
            print(f"\n🔍 开始处理: {user_input}")
            
            # 使用ADK Runner执行任务
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types
            
            session_service = InMemorySessionService()
            session = await session_service.create_session(
                state={}, app_name='researchmind', user_id='user'
            )
            
            runner = Runner(
                app_name='researchmind',
                agent=coordinator_agent,
                session_service=session_service,
            )
            
            content = types.Content(role='user', parts=[types.Part(text=user_input)])
            
            print("🤖 智能体正在处理您的请求...")
            events_async = runner.run_async(
                session_id=session.id, 
                user_id=session.user_id, 
                new_message=content
            )
            
            async for event in events_async:
                if hasattr(event, 'content') and event.content:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            print(f"📊 {part.text}")
            
            print(f"\n✅ 处理完成!")
            
        except KeyboardInterrupt:
            print("\n\n👋 感谢使用 ResearchMind!")
            break
        except Exception as e:
            logger.error(f"处理请求时发生错误: {e}")
            print(f"❌ 错误: {e}")

def print_help():
    """打印帮助信息"""
    help_text = """
🔧 ResearchMind MCP架构使用指南:

📚 文献调研:
  - "调研锂电池材料的最新进展"
  - "搜索钙钛矿太阳能电池相关论文"

🗄️ 数据库检索:
  - "查找石墨烯的晶体结构"
  - "搜索高熵合金的性质数据"

⚛️ 仿真模拟:
  - "计算硅的能带结构"
  - "模拟水分子的动力学行为"

🧪 实验设计:
  - "设计合成石墨烯的实验方案"
  - "优化催化剂制备工艺参数"

🔄 综合任务:
  - "我想研究新型储能材料，请提供完整的研究方案"
  - "帮我设计一个关于超导材料的研究项目"

🚀 工作流模式:
  - Sequential: 顺序执行各个步骤 (文献→数据库→仿真→实验)
  - Parallel: 并行执行多个任务 (同时进行多个研究任务)
  - Hybrid: 智能混合模式 (根据情况自动选择策略)
  - Specialized: 专项研究模式 (针对特定研究类型优化)

🤖 可用智能体:
  - root_agent: 主协调器 (推荐)
  - literature_agent: 文献调研专家
  - database_agent: 数据库检索专家
  - simulation_agent: 仿真计算专家
  - experiment_agent: 实验设计专家

💡 使用技巧:
  - 使用 --demo 查看智能体演示
  - 使用 --agent 指定特定智能体
  - 使用 --workflow 选择工作流模式
    """
    print(help_text)

async def research_mode(coordinator_agent: LlmAgent, topic: str, workflow_type: str):
    """直接研究模式"""
    print(f"🔍 开始研究: {topic}")
    print(f"🔄 工作流模式: {workflow_type}")
    
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
        
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            state={}, app_name='researchmind', user_id='user'
        )
        
        runner = Runner(
            app_name='researchmind',
            agent=coordinator_agent,
            session_service=session_service,
        )
        
        content = types.Content(role='user', parts=[types.Part(text=topic)])
        
        print("🤖 智能体正在处理您的研究请求...")
        events_async = runner.run_async(
            session_id=session.id, 
            user_id=session.user_id, 
            new_message=content
        )
        
        async for event in events_async:
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(f"📊 {part.text}")
        
        print(f"\n✅ 研究完成!")
        
    except Exception as e:
        logger.error(f"研究过程中发生错误: {e}")
        print(f"❌ 错误: {e}")

def start_adk_web(port: int):
    """启动ADK Web界面"""
    try:
        print(f"🌐 启动ADK Web界面，端口: {port}")
        print(f"🔗 访问地址: http://localhost:{port}")
        print("请在浏览器中选择 'research_coordinator' 智能体")
        
        # 启动adk web
        os.system(f"adk web --port {port}")
        
    except Exception as e:
        logger.error(f"启动ADK Web界面失败: {e}")

async def run_demo():
    """运行智能体演示"""
    print("🚀 启动ResearchMind智能体演示...")

    try:
        from examples.agent_demo import main as demo_main
        await demo_main()
    except ImportError:
        print("❌ 无法导入演示模块，请检查examples/agent_demo.py文件")
    except Exception as e:
        logger.error(f"演示运行失败: {e}")

async def main():
    """主函数"""
    parser = setup_cli()
    args = parser.parse_args()

    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # 演示模式
        if args.demo:
            await run_demo()
            return

        # 获取协调器智能体
        coordinator_agent = await get_coordinator_agent(args.workflow, args.agent)

        # ADK Web模式
        if args.web:
            start_adk_web(args.port)
            return

        # 部署模式
        if args.deploy:
            print(f"🚀 部署到 {args.deploy}...")
            # TODO: 实现部署逻辑
            return

        # 选择运行模式
        if args.research:
            await research_mode(coordinator_agent, args.research, args.workflow)
        elif args.interactive:
            await interactive_mode(coordinator_agent)
        else:
            # 默认交互模式
            await interactive_mode(coordinator_agent)

    except Exception as e:
        logger.error(f"程序运行失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
