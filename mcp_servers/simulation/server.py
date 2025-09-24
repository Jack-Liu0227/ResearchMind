#!/usr/bin/env python3
"""
仿真计算MCP服务器
提供MatterSim、计算设置、结果分析等仿真计算工具
"""

import asyncio
import json
import logging
from typing import Any, Dict, List
from datetime import datetime

# MCP Server Imports
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# 工具导入
from tools.mattersim_wrapper import MatterSimTool
from tools.calculation_setup import CalculationSetupTool
from tools.result_analysis import ResultAnalysisTool

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP服务器实例
app = Server("simulation-mcp-server")

# 初始化工具
mattersim_tool = MatterSimTool()
setup_tool = CalculationSetupTool()
analysis_tool = ResultAnalysisTool()

@app.list_tools()
async def list_simulation_tools() -> List[mcp_types.Tool]:
    """列出可用的仿真计算工具"""
    logger.info("MCP Server: 收到list_tools请求")
    
    tools = [
        mcp_types.Tool(
            name="setup_calculation",
            description="设置计算参数",
            inputSchema={
                "type": "object",
                "properties": {
                    "structure": {
                        "type": "string",
                        "description": "结构数据 (CIF格式或结构ID)"
                    },
                    "calculation_type": {
                        "type": "string",
                        "description": "计算类型",
                        "enum": ["energy", "optimization", "md", "phonon", "elastic"],
                        "default": "energy"
                    },
                    "accuracy": {
                        "type": "string",
                        "description": "计算精度",
                        "enum": ["low", "medium", "high", "ultra"],
                        "default": "medium"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "温度 (K)",
                        "default": 300
                    },
                    "pressure": {
                        "type": "number",
                        "description": "压力 (GPa)",
                        "default": 0.0
                    }
                },
                "required": ["structure"]
            }
        ),
        mcp_types.Tool(
            name="run_mattersim",
            description="运行MatterSim计算",
            inputSchema={
                "type": "object",
                "properties": {
                    "calculation_id": {
                        "type": "string",
                        "description": "计算任务ID"
                    },
                    "max_steps": {
                        "type": "integer",
                        "description": "最大计算步数",
                        "default": 1000
                    },
                    "convergence_threshold": {
                        "type": "number",
                        "description": "收敛阈值",
                        "default": 1e-6
                    },
                    "use_gpu": {
                        "type": "boolean",
                        "description": "是否使用GPU加速",
                        "default": True
                    }
                },
                "required": ["calculation_id"]
            }
        ),
        mcp_types.Tool(
            name="analyze_results",
            description="分析仿真结果",
            inputSchema={
                "type": "object",
                "properties": {
                    "calculation_id": {
                        "type": "string",
                        "description": "计算任务ID"
                    },
                    "analysis_type": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["energy", "forces", "stress", "dynamics", "structure", "electronic"]
                        },
                        "description": "分析类型列表",
                        "default": ["energy", "forces"]
                    },
                    "generate_plots": {
                        "type": "boolean",
                        "description": "是否生成图表",
                        "default": True
                    }
                },
                "required": ["calculation_id"]
            }
        ),
        mcp_types.Tool(
            name="optimize_structure",
            description="结构优化",
            inputSchema={
                "type": "object",
                "properties": {
                    "structure": {
                        "type": "string",
                        "description": "初始结构数据"
                    },
                    "optimization_method": {
                        "type": "string",
                        "description": "优化方法",
                        "enum": ["bfgs", "cg", "lbfgs", "fire"],
                        "default": "bfgs"
                    },
                    "force_tolerance": {
                        "type": "number",
                        "description": "力收敛标准 (eV/Å)",
                        "default": 0.01
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "最大迭代次数",
                        "default": 200
                    }
                },
                "required": ["structure"]
            }
        ),
        mcp_types.Tool(
            name="calculate_properties",
            description="计算物理性质",
            inputSchema={
                "type": "object",
                "properties": {
                    "structure": {
                        "type": "string",
                        "description": "结构数据"
                    },
                    "properties": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["band_structure", "dos", "elastic_constants", "phonon_spectrum", "thermal_properties"]
                        },
                        "description": "要计算的性质列表",
                        "default": ["band_structure", "dos"]
                    },
                    "k_point_density": {
                        "type": "number",
                        "description": "k点密度",
                        "default": 0.2
                    }
                },
                "required": ["structure"]
            }
        )
    ]
    
    logger.info(f"MCP Server: 返回{len(tools)}个工具")
    return tools

@app.call_tool()
async def call_simulation_tool(name: str, arguments: Dict[str, Any]) -> List[mcp_types.Content]:
    """执行仿真计算工具调用"""
    logger.info(f"MCP Server: 收到工具调用请求 '{name}' 参数: {arguments}")
    
    try:
        if name == "setup_calculation":
            result = await setup_tool.setup_calculation(
                structure=arguments["structure"],
                calculation_type=arguments.get("calculation_type", "energy"),
                accuracy=arguments.get("accuracy", "medium"),
                temperature=arguments.get("temperature", 300),
                pressure=arguments.get("pressure", 0.0)
            )
        
        elif name == "run_mattersim":
            result = await mattersim_tool.run_calculation(
                calculation_id=arguments["calculation_id"],
                max_steps=arguments.get("max_steps", 1000),
                convergence_threshold=arguments.get("convergence_threshold", 1e-6),
                use_gpu=arguments.get("use_gpu", True)
            )
        
        elif name == "analyze_results":
            result = await analysis_tool.analyze_results(
                calculation_id=arguments["calculation_id"],
                analysis_type=arguments.get("analysis_type", ["energy", "forces"]),
                generate_plots=arguments.get("generate_plots", True)
            )
        
        elif name == "optimize_structure":
            result = await mattersim_tool.optimize_structure(
                structure=arguments["structure"],
                optimization_method=arguments.get("optimization_method", "bfgs"),
                force_tolerance=arguments.get("force_tolerance", 0.01),
                max_iterations=arguments.get("max_iterations", 200)
            )
        
        elif name == "calculate_properties":
            result = await mattersim_tool.calculate_properties(
                structure=arguments["structure"],
                properties=arguments.get("properties", ["band_structure", "dos"]),
                k_point_density=arguments.get("k_point_density", 0.2)
            )
        
        else:
            error_msg = f"未知工具: {name}"
            logger.error(f"MCP Server: {error_msg}")
            return [mcp_types.TextContent(
                type="text", 
                text=json.dumps({"error": error_msg}, ensure_ascii=False)
            )]
        
        logger.info(f"MCP Server: 工具 '{name}' 执行成功")
        
        # 格式化结果
        response_text = json.dumps(result, ensure_ascii=False, indent=2)
        return [mcp_types.TextContent(type="text", text=response_text)]
        
    except Exception as e:
        error_msg = f"执行工具 '{name}' 时发生错误: {str(e)}"
        logger.error(f"MCP Server: {error_msg}")
        return [mcp_types.TextContent(
            type="text", 
            text=json.dumps({"error": error_msg}, ensure_ascii=False)
        )]

async def run_stdio_server():
    """运行stdio MCP服务器"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("仿真计算MCP服务器启动，等待客户端连接...")
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
        logger.info("仿真计算MCP服务器运行结束")

if __name__ == "__main__":
    logger.info("启动仿真计算MCP服务器...")
    try:
        asyncio.run(run_stdio_server())
    except KeyboardInterrupt:
        logger.info("仿真计算MCP服务器被用户中断")
    except Exception as e:
        logger.error(f"仿真计算MCP服务器发生错误: {e}")
    finally:
        logger.info("仿真计算MCP服务器退出")
