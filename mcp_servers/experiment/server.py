#!/usr/bin/env python3
"""
实验设计MCP服务器
提供实验方案设计、参数优化、风险评估等实验设计工具
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
from tools.design_optimizer import DesignOptimizerTool
from tools.risk_assessment import RiskAssessmentTool
from tools.protocol_generator import ProtocolGeneratorTool

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP服务器实例
app = Server("experiment-design-mcp-server")

# 初始化工具
design_tool = DesignOptimizerTool()
risk_tool = RiskAssessmentTool()
protocol_tool = ProtocolGeneratorTool()

@app.list_tools()
async def list_experiment_tools() -> List[mcp_types.Tool]:
    """列出可用的实验设计工具"""
    logger.info("MCP Server: 收到list_tools请求")
    
    tools = [
        mcp_types.Tool(
            name="design_experiment",
            description="设计实验方案",
            inputSchema={
                "type": "object",
                "properties": {
                    "research_objective": {
                        "type": "string",
                        "description": "研究目标"
                    },
                    "target_material": {
                        "type": "string",
                        "description": "目标材料"
                    },
                    "synthesis_method": {
                        "type": "string",
                        "description": "合成方法",
                        "enum": ["sol_gel", "hydrothermal", "solid_state", "chemical_vapor_deposition", "electrochemical"],
                        "default": "sol_gel"
                    },
                    "characterization_methods": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["xrd", "sem", "tem", "xps", "ftir", "raman", "uv_vis", "electrochemical"]
                        },
                        "description": "表征方法列表",
                        "default": ["xrd", "sem"]
                    },
                    "budget_constraint": {
                        "type": "number",
                        "description": "预算限制 (万元)",
                        "default": 10
                    },
                    "time_constraint": {
                        "type": "number",
                        "description": "时间限制 (周)",
                        "default": 12
                    }
                },
                "required": ["research_objective", "target_material"]
            }
        ),
        mcp_types.Tool(
            name="optimize_parameters",
            description="优化实验参数",
            inputSchema={
                "type": "object",
                "properties": {
                    "experiment_type": {
                        "type": "string",
                        "description": "实验类型"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "待优化参数",
                        "properties": {
                            "temperature": {
                                "type": "object",
                                "properties": {
                                    "min": {"type": "number"},
                                    "max": {"type": "number"},
                                    "current": {"type": "number"}
                                }
                            },
                            "pressure": {
                                "type": "object",
                                "properties": {
                                    "min": {"type": "number"},
                                    "max": {"type": "number"},
                                    "current": {"type": "number"}
                                }
                            },
                            "time": {
                                "type": "object",
                                "properties": {
                                    "min": {"type": "number"},
                                    "max": {"type": "number"},
                                    "current": {"type": "number"}
                                }
                            }
                        }
                    },
                    "optimization_method": {
                        "type": "string",
                        "description": "优化方法",
                        "enum": ["bayesian", "genetic_algorithm", "grid_search", "random_search"],
                        "default": "bayesian"
                    },
                    "target_property": {
                        "type": "string",
                        "description": "目标性质"
                    }
                },
                "required": ["experiment_type", "parameters", "target_property"]
            }
        ),
        mcp_types.Tool(
            name="assess_risk",
            description="评估实验风险",
            inputSchema={
                "type": "object",
                "properties": {
                    "experiment_design": {
                        "type": "object",
                        "description": "实验设计方案"
                    },
                    "chemicals": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "使用的化学品列表"
                    },
                    "equipment": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "使用的设备列表"
                    },
                    "safety_level": {
                        "type": "string",
                        "description": "安全等级要求",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium"
                    }
                },
                "required": ["experiment_design"]
            }
        ),
        mcp_types.Tool(
            name="generate_protocol",
            description="生成实验协议",
            inputSchema={
                "type": "object",
                "properties": {
                    "experiment_design": {
                        "type": "object",
                        "description": "实验设计方案"
                    },
                    "detail_level": {
                        "type": "string",
                        "description": "详细程度",
                        "enum": ["basic", "detailed", "comprehensive"],
                        "default": "detailed"
                    },
                    "include_safety": {
                        "type": "boolean",
                        "description": "是否包含安全说明",
                        "default": True
                    },
                    "include_troubleshooting": {
                        "type": "boolean",
                        "description": "是否包含故障排除",
                        "default": True
                    }
                },
                "required": ["experiment_design"]
            }
        ),
        mcp_types.Tool(
            name="estimate_cost",
            description="估算实验成本",
            inputSchema={
                "type": "object",
                "properties": {
                    "experiment_design": {
                        "type": "object",
                        "description": "实验设计方案"
                    },
                    "scale": {
                        "type": "string",
                        "description": "实验规模",
                        "enum": ["lab_scale", "pilot_scale", "industrial_scale"],
                        "default": "lab_scale"
                    },
                    "location": {
                        "type": "string",
                        "description": "实验地点",
                        "default": "university_lab"
                    },
                    "include_labor": {
                        "type": "boolean",
                        "description": "是否包含人工成本",
                        "default": True
                    }
                },
                "required": ["experiment_design"]
            }
        )
    ]
    
    logger.info(f"MCP Server: 返回{len(tools)}个工具")
    return tools

@app.call_tool()
async def call_experiment_tool(name: str, arguments: Dict[str, Any]) -> List[mcp_types.Content]:
    """执行实验设计工具调用"""
    logger.info(f"MCP Server: 收到工具调用请求 '{name}' 参数: {arguments}")
    
    try:
        if name == "design_experiment":
            result = await design_tool.design_experiment(
                research_objective=arguments["research_objective"],
                target_material=arguments["target_material"],
                synthesis_method=arguments.get("synthesis_method", "sol_gel"),
                characterization_methods=arguments.get("characterization_methods", ["xrd", "sem"]),
                budget_constraint=arguments.get("budget_constraint", 10),
                time_constraint=arguments.get("time_constraint", 12)
            )
        
        elif name == "optimize_parameters":
            result = await design_tool.optimize_parameters(
                experiment_type=arguments["experiment_type"],
                parameters=arguments["parameters"],
                optimization_method=arguments.get("optimization_method", "bayesian"),
                target_property=arguments["target_property"]
            )
        
        elif name == "assess_risk":
            result = await risk_tool.assess_risk(
                experiment_design=arguments["experiment_design"],
                chemicals=arguments.get("chemicals", []),
                equipment=arguments.get("equipment", []),
                safety_level=arguments.get("safety_level", "medium")
            )
        
        elif name == "generate_protocol":
            result = await protocol_tool.generate_protocol(
                experiment_design=arguments["experiment_design"],
                detail_level=arguments.get("detail_level", "detailed"),
                include_safety=arguments.get("include_safety", True),
                include_troubleshooting=arguments.get("include_troubleshooting", True)
            )
        
        elif name == "estimate_cost":
            result = await design_tool.estimate_cost(
                experiment_design=arguments["experiment_design"],
                scale=arguments.get("scale", "lab_scale"),
                location=arguments.get("location", "university_lab"),
                include_labor=arguments.get("include_labor", True)
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
        logger.info("实验设计MCP服务器启动，等待客户端连接...")
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
        logger.info("实验设计MCP服务器运行结束")

if __name__ == "__main__":
    logger.info("启动实验设计MCP服务器...")
    try:
        asyncio.run(run_stdio_server())
    except KeyboardInterrupt:
        logger.info("实验设计MCP服务器被用户中断")
    except Exception as e:
        logger.error(f"实验设计MCP服务器发生错误: {e}")
    finally:
        logger.info("实验设计MCP服务器退出")
