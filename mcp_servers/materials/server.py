#!/usr/bin/env python3
"""
材料数据库MCP服务器
提供Materials Project、CrystaLLM、结构分析等材料科学工具
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
from tools.materials_project import MaterialsProjectTool
from tools.crystallm_wrapper import CrystaLLMTool
from tools.structure_analysis import StructureAnalysisTool

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP服务器实例
app = Server("materials-database-mcp-server")

# 初始化工具
materials_tool = MaterialsProjectTool()
crystallm_tool = CrystaLLMTool()
analysis_tool = StructureAnalysisTool()

@app.list_tools()
async def list_materials_tools() -> List[mcp_types.Tool]:
    """列出可用的材料数据库工具"""
    logger.info("MCP Server: 收到list_tools请求")
    
    tools = [
        mcp_types.Tool(
            name="search_structure",
            description="搜索晶体结构数据库",
            inputSchema={
                "type": "object",
                "properties": {
                    "formula": {
                        "type": "string",
                        "description": "化学式，如 'Li2O', 'Fe2O3'"
                    },
                    "elements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "元素列表，如 ['Li', 'O']"
                    },
                    "crystal_system": {
                        "type": "string",
                        "description": "晶系",
                        "enum": ["cubic", "tetragonal", "orthorhombic", "hexagonal", "trigonal", "monoclinic", "triclinic"]
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大结果数量",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        mcp_types.Tool(
            name="generate_structure",
            description="使用CrystaLLM生成新结构",
            inputSchema={
                "type": "object",
                "properties": {
                    "composition": {
                        "type": "string",
                        "description": "目标组成，如 'Li2O'"
                    },
                    "crystal_system": {
                        "type": "string",
                        "description": "目标晶系",
                        "enum": ["cubic", "tetragonal", "orthorhombic", "hexagonal", "trigonal", "monoclinic", "triclinic"]
                    },
                    "space_group": {
                        "type": "integer",
                        "description": "空间群编号 (1-230)"
                    },
                    "num_structures": {
                        "type": "integer",
                        "description": "生成结构数量",
                        "default": 5
                    }
                },
                "required": ["composition"]
            }
        ),
        mcp_types.Tool(
            name="predict_properties",
            description="预测材料性质",
            inputSchema={
                "type": "object",
                "properties": {
                    "structure": {
                        "type": "string",
                        "description": "结构数据 (CIF格式或结构ID)"
                    },
                    "properties": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["band_gap", "formation_energy", "elastic_modulus", "density", "magnetic_moment"]
                        },
                        "description": "要预测的性质列表",
                        "default": ["band_gap", "formation_energy"]
                    }
                },
                "required": ["structure"]
            }
        ),
        mcp_types.Tool(
            name="validate_structure",
            description="验证结构稳定性",
            inputSchema={
                "type": "object",
                "properties": {
                    "structure": {
                        "type": "string",
                        "description": "结构数据 (CIF格式)"
                    },
                    "check_symmetry": {
                        "type": "boolean",
                        "description": "是否检查对称性",
                        "default": True
                    },
                    "check_bonding": {
                        "type": "boolean",
                        "description": "是否检查键合合理性",
                        "default": True
                    }
                },
                "required": ["structure"]
            }
        ),
        mcp_types.Tool(
            name="visualize_structure",
            description="可视化晶体结构",
            inputSchema={
                "type": "object",
                "properties": {
                    "structure": {
                        "type": "string",
                        "description": "结构数据 (CIF格式或结构ID)"
                    },
                    "view_type": {
                        "type": "string",
                        "description": "视图类型",
                        "enum": ["ball_stick", "polyhedra", "wireframe", "space_filling"],
                        "default": "ball_stick"
                    },
                    "show_unit_cell": {
                        "type": "boolean",
                        "description": "是否显示晶胞",
                        "default": True
                    }
                },
                "required": ["structure"]
            }
        )
    ]
    
    logger.info(f"MCP Server: 返回{len(tools)}个工具")
    return tools

@app.call_tool()
async def call_materials_tool(name: str, arguments: Dict[str, Any]) -> List[mcp_types.Content]:
    """执行材料数据库工具调用"""
    logger.info(f"MCP Server: 收到工具调用请求 '{name}' 参数: {arguments}")
    
    try:
        if name == "search_structure":
            result = await materials_tool.search_structure(
                formula=arguments.get("formula"),
                elements=arguments.get("elements"),
                crystal_system=arguments.get("crystal_system"),
                max_results=arguments.get("max_results", 10)
            )
        
        elif name == "generate_structure":
            result = await crystallm_tool.generate_structure(
                composition=arguments["composition"],
                crystal_system=arguments.get("crystal_system"),
                space_group=arguments.get("space_group"),
                num_structures=arguments.get("num_structures", 5)
            )
        
        elif name == "predict_properties":
            result = await analysis_tool.predict_properties(
                structure=arguments["structure"],
                properties=arguments.get("properties", ["band_gap", "formation_energy"])
            )
        
        elif name == "validate_structure":
            result = await analysis_tool.validate_structure(
                structure=arguments["structure"],
                check_symmetry=arguments.get("check_symmetry", True),
                check_bonding=arguments.get("check_bonding", True)
            )
        
        elif name == "visualize_structure":
            result = await analysis_tool.visualize_structure(
                structure=arguments["structure"],
                view_type=arguments.get("view_type", "ball_stick"),
                show_unit_cell=arguments.get("show_unit_cell", True)
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
        logger.info("材料数据库MCP服务器启动，等待客户端连接...")
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
        logger.info("材料数据库MCP服务器运行结束")

if __name__ == "__main__":
    logger.info("启动材料数据库MCP服务器...")
    try:
        asyncio.run(run_stdio_server())
    except KeyboardInterrupt:
        logger.info("材料数据库MCP服务器被用户中断")
    except Exception as e:
        logger.error(f"材料数据库MCP服务器发生错误: {e}")
    finally:
        logger.info("材料数据库MCP服务器退出")
