#!/usr/bin/env python3
"""
文献检索MCP服务器
提供ArXiv、Google Scholar、Web搜索等文献检索工具
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
from tools.arxiv_search import ArxivSearchTool
from tools.scholar_search import ScholarSearchTool
from tools.web_search import WebSearchTool
from tools.paper_analysis import PaperAnalysisTool

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP服务器实例
app = Server("literature-research-mcp-server")

# 初始化工具
arxiv_tool = ArxivSearchTool()
scholar_tool = ScholarSearchTool()
web_tool = WebSearchTool()
analysis_tool = PaperAnalysisTool()

@app.list_tools()
async def list_literature_tools() -> List[mcp_types.Tool]:
    """列出可用的文献检索工具"""
    logger.info("MCP Server: 收到list_tools请求")
    
    tools = [
        mcp_types.Tool(
            name="search_arxiv",
            description="搜索ArXiv论文数据库",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大结果数量",
                        "default": 10
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序方式",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "relevance"
                    }
                },
                "required": ["query"]
            }
        ),
        mcp_types.Tool(
            name="search_scholar",
            description="搜索Google Scholar学术论文",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大结果数量",
                        "default": 10
                    },
                    "year_low": {
                        "type": "integer",
                        "description": "起始年份"
                    },
                    "year_high": {
                        "type": "integer",
                        "description": "结束年份"
                    }
                },
                "required": ["query"]
            }
        ),
        mcp_types.Tool(
            name="search_web",
            description="网络搜索相关文献和资料",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大结果数量",
                        "default": 10
                    },
                    "site": {
                        "type": "string",
                        "description": "限制搜索的网站域名"
                    }
                },
                "required": ["query"]
            }
        ),
        mcp_types.Tool(
            name="analyze_paper",
            description="分析论文内容，提取关键信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_content": {
                        "type": "string",
                        "description": "论文内容或摘要"
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "分析类型",
                        "enum": ["summary", "methods", "results", "full"],
                        "default": "summary"
                    }
                },
                "required": ["paper_content"]
            }
        ),
        mcp_types.Tool(
            name="generate_report",
            description="生成文献调研报告",
            inputSchema={
                "type": "object",
                "properties": {
                    "papers": {
                        "type": "array",
                        "description": "论文列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "authors": {"type": "string"},
                                "abstract": {"type": "string"},
                                "url": {"type": "string"}
                            }
                        }
                    },
                    "research_topic": {
                        "type": "string",
                        "description": "研究主题"
                    },
                    "report_type": {
                        "type": "string",
                        "description": "报告类型",
                        "enum": ["brief", "detailed", "comprehensive"],
                        "default": "detailed"
                    }
                },
                "required": ["papers", "research_topic"]
            }
        )
    ]
    
    logger.info(f"MCP Server: 返回{len(tools)}个工具")
    return tools

@app.call_tool()
async def call_literature_tool(name: str, arguments: Dict[str, Any]) -> List[mcp_types.Content]:
    """执行文献检索工具调用"""
    logger.info(f"MCP Server: 收到工具调用请求 '{name}' 参数: {arguments}")
    
    try:
        if name == "search_arxiv":
            result = await arxiv_tool.search(
                query=arguments["query"],
                max_results=arguments.get("max_results", 10),
                sort_by=arguments.get("sort_by", "relevance")
            )
        
        elif name == "search_scholar":
            result = await scholar_tool.search(
                query=arguments["query"],
                max_results=arguments.get("max_results", 10),
                year_low=arguments.get("year_low"),
                year_high=arguments.get("year_high")
            )
        
        elif name == "search_web":
            result = await web_tool.search(
                query=arguments["query"],
                max_results=arguments.get("max_results", 10),
                site=arguments.get("site")
            )
        
        elif name == "analyze_paper":
            result = await analysis_tool.analyze(
                paper_content=arguments["paper_content"],
                analysis_type=arguments.get("analysis_type", "summary")
            )
        
        elif name == "generate_report":
            result = await analysis_tool.generate_report(
                papers=arguments["papers"],
                research_topic=arguments["research_topic"],
                report_type=arguments.get("report_type", "detailed")
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
        logger.info("文献检索MCP服务器启动，等待客户端连接...")
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
        logger.info("文献检索MCP服务器运行结束")

if __name__ == "__main__":
    logger.info("启动文献检索MCP服务器...")
    try:
        asyncio.run(run_stdio_server())
    except KeyboardInterrupt:
        logger.info("文献检索MCP服务器被用户中断")
    except Exception as e:
        logger.error(f"文献检索MCP服务器发生错误: {e}")
    finally:
        logger.info("文献检索MCP服务器退出")
