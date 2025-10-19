"""
Paper Search MCP Server
Provides tools for searching academic papers from ArXiv using the arxiv library.
"""
import sys
from pathlib import Path
import argparse
import json
import os
import logging
from datetime import datetime


def get_api_base_url() -> str:
    """
    获取 API 基础 URL，支持多种配置方式

    优先级：
    1. VITE_API_URL（前端调用的API地址）
    2. RESEARCHMIND_HTTP_HOST + RESEARCHMIND_HTTP_PORT

    支持相对路径（如 /api）和完整 URL
    """
    api_url = os.getenv("VITE_API_URL")

    if api_url:
        # 如果是相对路径，需要转换为完整 URL
        # 但在后端无法自动检测前端的域名，所以相对路径需要前端处理
        # 后端只返回相对路径，前端会自动转换
        if api_url.startswith('/'):
            # 相对路径：直接返回，前端会处理
            return api_url
        else:
            # 完整 URL：直接返回
            return api_url

    # 备选方案：使用 RESEARCHMIND_HTTP_HOST + RESEARCHMIND_HTTP_PORT
    http_host = os.getenv("RESEARCHMIND_HTTP_HOST", "127.0.0.1")
    http_port = os.getenv("RESEARCHMIND_HTTP_PORT", "50002")

    # 如果监听地址是 0.0.0.0，使用 127.0.0.1 以支持本地访问
    if http_host == "0.0.0.0":
        http_host = "127.0.0.1"

    return f"http://{http_host}:{http_port}"


def get_download_url(file_path: str) -> str:
    """
    生成文件下载 URL

    始终返回相对路径（不包含 /api 前缀），Nginx 代理会添加
    这样可以支持任何部署方式（直接访问、反向代理等）

    参考 ImageHandler 的实现逻辑
    """
    # 规范化文件路径：移除 ./ 前缀，转换反斜杠为正斜杠
    file_path = file_path.replace('\\', '/').lstrip('./')
    # 移除前缀 "mcp_servers/paper_search/" 如果存在
    if file_path.startswith('mcp_servers/paper_search/'):
        file_path = file_path[len('mcp_servers/paper_search/'):]
    elif file_path.startswith('paper_search/'):
        file_path = file_path[len('paper_search/'):]

    # 始终返回相对路径：/download/...（不包含 /api 前缀）
    # Nginx 代理会添加 /api 前缀，前端的 resolveFileUrl() 函数会处理转换为完整 URL
    return f"api/api/download/{file_path}"
from typing import List, Dict, Any, Optional

from fastmcp import FastMCP
import structlog

# Suppress PyPDF2 warnings about unknown widths
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PyPDF2")

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import context manager (including data layer and service management)
from modules.context_manager import (
    ChromaVectorStore,
    ingest_papers_to_vector_store as ingest_papers_impl,
    get_embedding_service,
    get_vector_store
)

# Import all business logic modules
from modules import (
    # ArXiv
    search_arxiv_papers as search_arxiv_papers_impl,
    search_papers_by_author as search_papers_by_author_impl,
    get_arxiv_paper_content as get_arxiv_paper_content_impl,
    # Tavily
    search_web as search_web_impl,
    search_academic_web as search_academic_web_impl,
    search_news as search_news_impl,
    is_tavily_available,
    # Planning
    generate_research_plan as generate_research_plan_impl,
    # Analysis
    batch_paper_analysis as batch_paper_analysis_impl,
    # Reporting
    generate_research_report_with_data_collection,
    # Export Tools
    save_papers_to_csv as save_papers_to_csv_impl,
)

# Import unified tools
from modules.unified_tools import (
    search_papers as search_papers_unified,
    get_paper_content as get_paper_content_unified,
    download_paper_file as download_paper_unified,
    get_paper_info as get_paper_info_unified,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# 辅助函数：清理和验证返回内容
# ============================================================================

def sanitize_string_for_json(text: str, max_length: int = 5000) -> str:
    """
    清理字符串，确保可以安全地序列化为 JSON

    Args:
        text: 要清理的字符串
        max_length: 最大长度限制

    Returns:
        清理后的字符串
    """
    if not text:
        return ""

    # 转换为字符串（如果不是）
    if not isinstance(text, str):
        text = str(text)

    # 移除或替换特殊字符
    # 1. 移除控制字符（除了常见的空白字符）
    import re
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # 2. 替换换行符为空格（保持文本连续性）
    text = text.replace('\n', ' ')
    text = text.replace('\r', ' ')
    text = text.replace('\t', ' ')

    # 3. 移除多余的空格
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # 注意：不要手动转义引号和反斜杠，JSON 序列化器会自动处理

    # 5. 截断过长的字符串
    if len(text) > max_length:
        text = text[:max_length] + "... (truncated for JSON safety)"

    return text


def sanitize_tool_response(data: Any, max_string_length: int = 5000) -> Any:
    """
    递归清理工具返回值中的所有字符串，防止 JSON 解析错误

    Args:
        data: 要清理的数据
        max_string_length: 字符串最大长度

    Returns:
        清理后的数据
    """
    if isinstance(data, str):
        return sanitize_string_for_json(data, max_string_length)
    elif isinstance(data, dict):
        return {
            key: sanitize_tool_response(value, max_string_length)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_tool_response(item, max_string_length) for item in data]
    else:
        return data


def parse_args():
    """Parse command line arguments for MCP server."""
    parser = argparse.ArgumentParser(description="Paper Search MCP Server")
    parser.add_argument('--port', type=int, default=50005, help='Server port (default: 50005)')
    parser.add_argument('--host', default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--transport', default='stdio',
                       choices=['stdio', 'http'],
                       help='Transport protocol (default: stdio)')
    try:
        args = parser.parse_args()
    except SystemExit:
        class Args:
            port = 50005
            host = '0.0.0.0'
            transport = 'stdio'
            log_level = 'INFO'
        args = Args()
    return args

args = parse_args()
mcp = FastMCP("paper_search")  # Don't specify host/port here, will be set in uvicorn.run()

# Health check will be handled by the HTTP server when running with uvicorn


# ============================================================================
# Helper Functions (辅助函数)
# ============================================================================

async def _generate_expanded_queries(original_query: str, num_queries: int = 3) -> List[str]:
    """
    使用 LLM 生成多个相关的检索词

    Args:
        original_query: 原始查询
        num_queries: 生成的检索词数量

    Returns:
        包含原始查询和扩展查询的列表
    """
    try:
        from litellm import completion
        import os

        model = os.getenv('MODEL_USE', 'gemini/gemini-2.5-flash')

        prompt = f"""请根据以下研究问题生成 {num_queries} 个不同的英文检索词，用于学术文献搜索。

原始问题：{original_query}

要求：
1. 生成 {num_queries} 个不同的检索词
2. 每个检索词应该从不同的角度描述相同的研究主题
3. 使用英文关键词（适合 ArXiv 等学术数据库）
4. 每个检索词应该简洁（3-6个单词）
5. 包含原始查询（如果是英文）或其英文翻译

请只返回检索词列表，每行一个，不要添加编号或其他说明。

示例格式：
machine learning alloy design
AI for materials science
deep learning metallurgy
"""

        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        result_text = response.choices[0].message.content.strip()

        # 解析结果
        queries = []
        for line in result_text.split('\n'):
            line = line.strip()
            # 移除编号（如果有）
            if line and not line.startswith('#'):
                # 移除可能的编号前缀（1. 2. 等）
                import re
                line = re.sub(r'^\d+[\.\)]\s*', '', line)
                if line:
                    queries.append(line)

        # 确保包含原始查询
        if original_query not in queries:
            queries.insert(0, original_query)

        # 限制数量
        queries = queries[:num_queries]

        logger.info(f"Generated {len(queries)} expanded queries from '{original_query}'")
        return queries

    except Exception as e:
        logger.error(f"Failed to generate expanded queries: {e}")
        # 如果失败，返回原始查询
        return [original_query]


# ============================================================================
# Search Agent 工具 (7个)
# ============================================================================
# 职责：只负责检索论文信息，不做分析、下载、总结等操作

# --- 规划工具 (1个) ---

@mcp.tool()
async def generate_research_plan(user_intent: str, max_steps: int = 3) -> Dict[str, Any]:
    """
    Generate a research plan with sequential steps from user intent.
    Automatically translates Chinese queries to English for ArXiv search.

    ⚠️ 重要：Search Agent 必须先调用此工具优化搜索词！

    Args:
        user_intent: User's research intent (中文或英文)
        max_steps: Maximum number of research steps (default: 3)

    Returns:
        Dict containing research plan with optimized query:
        - primary_query: 优化后的英文搜索词
        - steps: 研究步骤列表
    """
    return await generate_research_plan_impl(user_intent=user_intent, max_steps=max_steps)


# --- 综合搜索 (1个，统一接口) ---

@mcp.tool()
async def search_papers(
    query: str,
    sources: List[str] = None,
    max_results: int = 3,
    session_id: str = None,
    expand_query: bool = False,
    num_expanded_queries: int = 3
) -> Dict[str, Any]:
    """
    统一的文献搜索接口（多源搜索）

    ⚠️ 推荐使用：默认搜索所有源，自动去重和标准化字段
    ⚠️ 自动保存：自动调用 save_papers_to_csv 保存检索结果
    ⚠️ 新功能：支持自动生成多个检索词进行综合搜索（expand_query=True）

    Args:
        query: 搜索查询（建议使用英文关键词）
        sources: 搜索源列表 ['arxiv', 'tavily_academic', 'tavily']
                如果为None，则搜索所有可用源
        max_results: 每个源的最大结果数（默认: 3，以节省资源）
        session_id: 会话ID（用于保存搜索结果到文件，可选）
        expand_query: 是否自动生成多个检索词（默认: False）
        num_expanded_queries: 生成的检索词数量（默认: 3）

    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - papers: 统一格式的论文列表（已去重）
        - sources_used: 使用的搜索源
        - total_results: 总结果数
        - csv_file_path: CSV文件路径（服务器端）
        - csv_content: CSV文件内容（供下载）
        - queries_used: 使用的检索词列表（如果 expand_query=True）
        - message: 消息
    """
    logger.info("Unified search", query=query, sources=sources, max_results=max_results, session_id=session_id, expand_query=expand_query)

    # 如果没有提供 session_id，使用query生成一个唯一的session_id
    if not session_id:
        import hashlib
        import uuid
        from datetime import datetime

        # 使用 query + 时间戳 + 随机UUID 生成唯一的 session_id
        query_clean = query.lower().replace(' ', '_').replace('-', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]  # 使用UUID的前8位确保唯一性

        # 限制session_id长度为50字符,避免路径过长
        if len(query_clean) > 30:
            # 如果query太长,只使用部分query + 时间戳 + unique_id
            session_id = f"{query_clean[:30]}_{unique_id}"
        else:
            session_id = f"{query_clean}_{unique_id}"

        logger.info(f"Generated unique session_id from query: {session_id}")

    # 如果 expand_query=True，生成多个检索词
    queries_to_search = [query]
    if expand_query:
        logger.info(f"Expanding query: {query}")
        expanded_queries = await _generate_expanded_queries(query, num_expanded_queries)
        queries_to_search = expanded_queries
        logger.info(f"Generated {len(queries_to_search)} queries: {queries_to_search}")

    # 异步并行搜索多个检索词
    import asyncio

    async def search_single_query(q: str) -> List[Dict[str, Any]]:
        """异步搜索单个检索词"""
        try:
            logger.info(f"Searching with query: {q}")
            result = await search_papers_unified(query=q, sources=sources, max_results=max_results, session_id=session_id)
            if result.get('status') == 'success':
                papers = result.get('papers', [])
                logger.info(f"Found {len(papers)} papers for query: {q}")
                return papers
            else:
                logger.warning(f"Search failed for query: {q}")
                return []
        except Exception as e:
            logger.error(f"Error searching query '{q}': {e}")
            return []

    # 并行执行所有搜索任务
    if len(queries_to_search) > 1:
        # 多个检索词时使用并行执行
        logger.info(f"Executing {len(queries_to_search)} searches in parallel...")
        search_tasks = [search_single_query(q) for q in queries_to_search]
        search_results = await asyncio.gather(*search_tasks)
        all_papers = []
        for papers in search_results:
            all_papers.extend(papers)
    else:
        # 单个检索词时直接执行
        all_papers = await search_single_query(queries_to_search[0])

    # 去重（基于 paper_id）
    unique_papers = {}
    for paper in all_papers:
        paper_id = paper.get('paper_id') or paper.get('id')
        if paper_id and paper_id not in unique_papers:
            unique_papers[paper_id] = paper

    final_papers = list(unique_papers.values())
    logger.info(f"Total papers after deduplication: {len(final_papers)}")

    # 自动保存检索结果到 CSV 文件
    from modules.paper_manager.export_tools import save_papers_to_csv as save_csv_impl
    csv_result = save_csv_impl(
        papers=final_papers,
        session_id=session_id,
        topic=query,
        file_prefix='search_results'
    )

    # 构建简化版的papers列表(只包含重要信息)
    simplified_papers = []
    for paper in final_papers:
        simplified_papers.append({
            'title': paper.get('title', 'Unknown'),
            'url': paper.get('url', ''),
            'source': paper.get('source', 'unknown'),
            'published': paper.get('published', ''),
            'authors': paper.get('authors', [])[:3] if isinstance(paper.get('authors'), list) else []  # 只保留前3个作者
        })

    # 构建返回结果
    final_result = {
        'status': 'success',
        'papers': simplified_papers,  # 简化版papers
        'sources_used': sources or ['arxiv', 'tavily_academic', 'tavily'],
        'total_results': len(final_papers),
        'message': f'Found {len(final_papers)} unique papers, saved to CSV'
    }

    # 添加 CSV 文件下载URL
    if csv_result.get('file_path'):
        # 使用新的 get_download_url 函数生成下载URL
        download_url = get_download_url(csv_result['file_path'])
        final_result['csv_download_url'] = download_url
        final_result['csv_file_path'] = csv_result['file_path']  # 保留原始路径用于调试

    if expand_query:
        final_result['queries_used'] = queries_to_search

    return sanitize_tool_response(final_result)


# --- 单源搜索 (保留用于特定需求) ---

@mcp.tool()
async def search_papers_all_sources(
    topic: str,
    max_results_per_source: int = 3
) -> Dict[str, Any]:
    """
    使用所有可用搜索源检索论文 (ArXiv + Tavily Academic)

    ⚠️ 已废弃：建议使用 search_papers 工具（统一接口）

    Args:
        topic: 搜索主题 (建议使用英文关键词)
        max_results_per_source: 每个搜索源的最大结果数 (默认: 3，以节省资源)

    Returns:
        Dict containing:
        - papers: 合并后的论文列表
        - sources_used: 使用的搜索源
        - total_results: 总结果数
    """
    logger.info("Searching papers from all sources (deprecated)", topic=topic)

    # 使用统一接口
    result = await search_papers_unified(
        query=topic,
        sources=None,  # 搜索所有源
        max_results=max_results_per_source
    )

    return result


# --- ArXiv 搜索 (3个) ---

@mcp.tool()
async def search_arxiv_papers(topic: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search for papers on arXiv based on a topic and return detailed information.

    ⚠️ 重要提示: 在调用此工具前，必须先调用 generate_research_plan 进行规划！

    Args:
        topic: The topic to search for (建议使用英文关键词)
        max_results: Maximum number of results to retrieve (default: 3，以节省资源)

    Returns:
        List of dictionaries containing paper information:
        - paper_id: ArXiv paper ID
        - title: Paper title
        - authors: List of author names
        - summary: Paper abstract/summary
        - pdf_url: URL to download PDF
        - published: Publication date
        - categories: ArXiv categories
        - source: 'arxiv'
    """
    return search_arxiv_papers_impl(topic=topic, max_results=max_results, session_id=None)

@mcp.tool()
async def search_papers_by_author(author_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for papers by a specific author on ArXiv.

    Args:
        author_name: Name of the author to search for
        max_results: Maximum number of results to retrieve (default: 5)

    Returns:
        List of paper information dictionaries
    """
    return search_papers_by_author_impl(author_name=author_name, max_results=max_results)

@mcp.tool()
async def get_paper_info(paper_id: str, source: str = 'arxiv') -> Dict[str, Any]:
    """
    获取论文信息（统一接口）

    Args:
        paper_id: 论文ID
        source: 来源（arxiv, tavily等），默认arxiv

    Returns:
        统一格式的论文信息字典
    """
    return get_paper_info_unified(paper_id=paper_id, source=source)


# --- Tavily 搜索 (3个) ---

@mcp.tool()
async def tavily_search(query: str, max_results: int = 3, search_depth: str = "advanced") -> List[Dict[str, Any]]:
    """
    Perform web search using Tavily (for general web content).

    Args:
        query: Search query
        max_results: Maximum number of results to return (default: 3，以节省资源)
        search_depth: Search depth ("basic" or "advanced")

    Returns:
        List of search results with title, url, content, and score
    """
    return await search_web_impl(query=query, max_results=max_results, search_depth=search_depth)


@mcp.tool()
async def tavily_academic_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Perform academic-focused web search using Tavily.

    Args:
        query: Academic search query
        max_results: Maximum number of results to return

    Returns:
        List of academic search results
    """
    return await search_academic_web_impl(query=query, max_results=max_results, session_id=None)


@mcp.tool()
async def tavily_news_search(query: str, max_results: int = 5, days: int = 7) -> List[Dict[str, Any]]:
    """
    Search for recent news articles using Tavily.

    Args:
        query: News search query
        max_results: Maximum number of results to return
        days: Number of days to look back for news

    Returns:
        List of recent news articles
    """
    return await search_news_impl(query=query, max_results=max_results, days=days)

# ============================================================================
# Paper Manager Agent 工具 (7个)
# ============================================================================
# 职责：获取全文、生成摘要、管理文献（返回内容，不保存文件）

# --- 文献下载 (1个) ---

@mcp.tool()
async def download_paper(paper: Dict[str, Any], download_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    下载论文文件（统一接口）

    ⚠️ 注意：仅在用户明确要求保存文献时使用此工具！

    Args:
        paper: 论文信息字典（包含paper_id, source, url等）
        download_dir: 下载目录（默认: ./papers）

    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - file_path: 下载的文件路径
        - message: 消息
    """
    return download_paper_unified(paper=paper, download_dir=download_dir)


# --- 通用内容获取 (2个，统一接口) ---

@mcp.tool()
async def get_paper_content(
    paper: Dict[str, Any],
    prefer_fulltext: bool = True
) -> Dict[str, Any]:
    """
    获取论文内容（统一接口）

    根据论文来源自动选择最佳内容获取方式。
    支持ArXiv PDF、通用URL PDF、通用URL HTML。
    失败时自动回退到摘要。

    Args:
        paper: 论文信息字典（包含paper_id, source, url, abstract等）
        prefer_fulltext: 是否优先获取全文（否则只返回摘要）

    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - content: 文本内容
        - metadata: 元数据（source_type, fallback等）
    """
    return get_paper_content_unified(paper=paper, prefer_fulltext=prefer_fulltext)


@mcp.tool()
async def fetch_papers_content(
    papers: List[Dict[str, Any]],
    prefer_fulltext: bool = True
) -> Dict[str, Any]:
    """
    批量获取论文内容（异步并行执行）

    为每篇论文获取全文或摘要，使用异步并行执行以提高效率。
    失败时自动回退到摘要。

    Args:
        papers: 论文列表（每篇包含paper_id, source, url, abstract等）
        prefer_fulltext: 是否优先获取全文（否则只返回摘要）

    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - papers_with_content: 包含内容的论文列表
        - summary: 获取摘要（成功/失败数量）
    """
    import asyncio
    from modules.paper_manager.content_fetcher import get_paper_content_by_source

    logger.info(f"Fetching content for {len(papers)} papers (async, max 5 concurrent)...")

    # 异步获取单篇论文内容
    async def fetch_single_paper(i: int, paper: Dict[str, Any]) -> tuple:
        """异步获取单篇论文内容"""
        try:
            logger.info(f"Fetching content {i}/{len(papers)}: {paper.get('title', 'Unknown')[:50]}...")

            if not prefer_fulltext:
                # 只使用摘要
                enriched_paper = paper.copy()
                enriched_paper['full_text'] = paper.get('abstract', '')
                enriched_paper['content_metadata'] = {'source_type': 'abstract', 'fallback': False}
                return (enriched_paper, 'success', False)

            # 获取全文（使用 executor 包装同步操作）
            loop = asyncio.get_event_loop()
            content_result = await loop.run_in_executor(
                None,
                lambda: get_paper_content_by_source(paper, paper.get('source'))
            )

            enriched_paper = paper.copy()
            enriched_paper['full_text'] = content_result.get('content', '')
            enriched_paper['content_metadata'] = content_result.get('metadata', {})

            # 判断是否使用了回退
            is_fallback = content_result.get('metadata', {}).get('fallback', False)
            status = 'fallback' if is_fallback else 'success'

            if is_fallback:
                logger.warning(f"Fallback to abstract for: {paper.get('title', 'Unknown')[:50]}")
            else:
                logger.info(f"Successfully fetched content for: {paper.get('title', 'Unknown')[:50]}")

            return (enriched_paper, status, is_fallback)

        except Exception as e:
            logger.error(f"Failed to fetch content for paper {i}: {e}")
            # 失败时使用摘要
            enriched_paper = paper.copy()
            enriched_paper['full_text'] = paper.get('abstract', '')
            enriched_paper['content_metadata'] = {'fallback': True, 'fallback_reason': str(e)}
            return (enriched_paper, 'error', True)

    # 使用信号量限制并发任务数量
    MAX_CONCURRENT = 8
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def bounded_fetch(i: int, paper: Dict[str, Any]) -> tuple:
        """限制并发的获取函数"""
        async with semaphore:
            return await fetch_single_paper(i, paper)

    # 并行执行所有任务
    tasks = [bounded_fetch(i, paper) for i, paper in enumerate(papers, 1)]
    results = await asyncio.gather(*tasks)

    # 处理结果
    papers_with_content = []
    success_count = 0
    fallback_count = 0
    error_count = 0

    for enriched_paper, status, is_fallback in results:
        papers_with_content.append(enriched_paper)
        if status == 'success':
            success_count += 1
        elif status == 'fallback':
            fallback_count += 1
        else:
            error_count += 1

    result = {
        'status': 'success',
        'papers_with_content': papers_with_content,
        'summary': {
            'total': len(papers),
            'success': success_count,
            'fallback': fallback_count,
            'error': error_count
        },
        'message': f'Fetched content for {len(papers)} papers: {success_count} success, {fallback_count} fallback, {error_count} error'
    }

    # 清理返回数据，防止 JSON 解析错误
    return sanitize_tool_response(result)


# --- 批量汇总 (1个) ---

@mcp.tool()
async def batch_paper_analysis(
    csv_file_path: str = None,
    papers: List[Dict[str, Any]] = None,
    session_id: str = None,
    topic: str = None
) -> Dict[str, Any]:
    """
    对多篇论文进行批量分析，并生成中文凝练摘要。

    功能：
    - 提取论文的摘要（Abstract）
    - 将摘要凝练翻译成中文
    - 提取关键信息：研究目标、方法、结果、创新点
    - 保存总结到 Markdown 文件和 CSV 文件

    Args:
        csv_file_path: CSV文件路径（优先使用，从CSV读取论文信息）
        papers: 论文列表（如果未提供csv_file_path，则使用此参数），每篇论文包含：
            - id/paper_id/arxiv_id: 论文ID（可选）
            - title: 论文标题
            - authors: 作者列表（可选）
            - abstract: 摘要（可选）
            - url/link: 论文链接（可选）
            - published/year: 发表时间（可选）
            - source: 来源（arxiv/tavily，可选）
        session_id: 会话ID（用于确定保存位置，可选）
        topic: 主题（用于确定保存位置，可选）

    Returns:
        包含批量分析结果的字典，每篇论文包含：
        - paper_id: 论文ID
        - title: 论文标题（英文）
        - authors: 作者列表
        - published: 发表时间
        - abstract_en: 英文摘要
        - abstract_zh: 中文凝练摘要
        - key_info: 关键信息（研究目标、方法、结果、创新点）
        - source: 来源
        - summary_file_path: 总结文件路径（MD格式）
        - csv_file_path: CSV文件路径
        - md_download_url: MD文件下载链接
        - csv_download_url: CSV文件下载链接
    """
    from modules.paper_manager.export_tools import save_summary_to_file, save_analysis_results_to_csv, read_papers_from_csv

    # 优先使用CSV文件
    if csv_file_path:
        logger.info(f"Reading papers from CSV: {csv_file_path}")
        papers = read_papers_from_csv(csv_file_path)
        if not papers:
            return {
                'status': 'error',
                'error': f'Failed to read papers from CSV: {csv_file_path}'
            }

        # 从CSV文件路径中提取session_id和topic
        # 路径格式: papers/{session_id}/xxx.csv
        if not session_id or not topic:
            from pathlib import Path
            csv_path = Path(csv_file_path)
            # 获取倒数第二个路径部分(session_id所在的文件夹名)
            if len(csv_path.parts) >= 2:
                extracted_session_id = csv_path.parts[-2]
                if not session_id:
                    session_id = extracted_session_id
                    logger.info(f"Extracted session_id from CSV path: {session_id}")
                if not topic:
                    # 使用session_id作为topic(去掉hash部分)
                    topic = extracted_session_id.rsplit('_', 1)[0] if '_' in extracted_session_id else extracted_session_id
                    logger.info(f"Extracted topic from session_id: {topic}")
    elif not papers:
        return {
            'status': 'error',
            'error': 'Must provide either csv_file_path or papers'
        }

    # 如果没有 session_id，从 papers 中提取或使用 topic 生成
    if not session_id:
        # 尝试从 papers 中提取 session_id（如果论文是从搜索结果来的）
        # 检查 session_metadata.json 所在的文件夹
        import json
        from pathlib import Path

        # 尝试从第一篇论文的 paper_id 推断 session_id
        if papers and len(papers) > 0:
            first_paper_id = papers[0].get('paper_id') or papers[0].get('id')
            logger.info(f"Searching for session_id using paper_id: {first_paper_id}")
            if first_paper_id:
                # 查找包含这篇论文的 papers_info.json
                # 使用绝对路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                papers_dir = Path(current_dir) / 'papers'
                logger.info(f"Searching in papers directory: {papers_dir}")

                if papers_dir.exists():
                    for session_folder in papers_dir.iterdir():
                        if session_folder.is_dir():
                            # 优先读取 session_metadata.json
                            metadata_file = session_folder / 'session_metadata.json'
                            if metadata_file.exists():
                                try:
                                    with open(metadata_file, 'r', encoding='utf-8') as f:
                                        metadata = json.load(f)
                                        # 检查这个 session 是否包含我们的论文
                                        papers_info_file = session_folder / 'papers_info.json'
                                        if papers_info_file.exists():
                                            with open(papers_info_file, 'r', encoding='utf-8') as pf:
                                                papers_info_data = json.load(pf)
                                                if first_paper_id in papers_info_data:
                                                    session_id = metadata.get('session_id')
                                                    logger.info(f"Found existing session_id from metadata: {session_id} in folder: {session_folder.name}")

                                                    # 重要：从 papers_info.json 中加载所有论文（包括 Tavily）
                                                    # 如果用户传入的 papers 列表不完整，补充完整
                                                    all_papers_from_file = list(papers_info_data.values())
                                                    if len(all_papers_from_file) > len(papers):
                                                        logger.info(f"Found {len(all_papers_from_file)} papers in papers_info.json, but only {len(papers)} were provided. Using all papers from file.")

                                                        # 清理和标准化论文数据
                                                        cleaned_papers = []
                                                        for paper in all_papers_from_file:
                                                            cleaned_paper = {
                                                                'paper_id': paper.get('paper_id', ''),
                                                                'id': paper.get('id', ''),
                                                                'title': paper.get('title', '')[:500],  # 限制长度
                                                                'authors': paper.get('authors', []),
                                                                'abstract': paper.get('abstract', paper.get('content', ''))[:2000],  # 限制长度
                                                                'url': paper.get('url', ''),
                                                                'published': paper.get('published', ''),
                                                                'source': paper.get('source', ''),
                                                            }
                                                            cleaned_papers.append(cleaned_paper)

                                                        papers = cleaned_papers

                                                    break
                                except Exception as e:
                                    logger.error(f"Error reading metadata from {session_folder}: {e}")

        # 如果还是没有 session_id，使用 topic 生成一个唯一的
        if not session_id and topic:
            import hashlib
            import uuid
            from datetime import datetime

            # 使用 topic + UUID 生成唯一的 session_id
            topic_clean = topic.lower().replace(' ', '_').replace('-', '_')
            unique_id = str(uuid.uuid4())[:8]  # 使用UUID的前8位确保唯一性

            # 限制session_id长度为50字符,避免路径过长
            if len(topic_clean) > 30:
                # 如果topic太长,只使用部分topic + unique_id
                session_id = f"{topic_clean[:30]}_{unique_id}"
            else:
                session_id = f"{topic_clean}_{unique_id}"

            logger.info(f"Generated unique session_id from topic: {session_id}")
        elif not session_id:
            # 如果都没有，生成一个随机的 session_id
            import uuid
            session_id = str(uuid.uuid4())[:8]
            logger.info(f"Generated random session_id: {session_id}")

    # 执行批量分析（异步并发执行）
    result = await batch_paper_analysis_impl(papers=papers)

    # 保存总结到 Markdown 文件
    if result.get('status') == 'success':
        summary_result = save_summary_to_file(
            summary_result=result,
            session_id=session_id,
            topic=topic,
            file_prefix='analysis'
        )
        if summary_result.get('file_path'):
            file_path = summary_result['file_path']
            result['summary_file_path'] = file_path
            # 使用新的 get_download_url 函数生成下载URL
            result['md_download_url'] = get_download_url(file_path)

        # 保存分析结果到 CSV 文件（包含中文摘要和关键信息）
        csv_result = save_analysis_results_to_csv(
            analysis_results=result.get('results', []),
            session_id=session_id,
            topic=topic,
            file_prefix='analysis_results'
        )
        if csv_result.get('file_path'):
            file_path = csv_result['file_path']
            result['csv_file_path'] = file_path
            # 使用新的 get_download_url 函数生成下载URL
            result['csv_download_url'] = get_download_url(file_path)

        # 简化results字段,只保留重要信息
        if 'results' in result:
            simplified_results = []
            for r in result['results']:
                if r.get('status') != 'error':
                    simplified_results.append({
                        'title': r.get('title', 'Unknown'),
                        'source': r.get('source', 'unknown'),
                        'pdf_url': r.get('pdf_url', r.get('url', '')),
                        'abstract_zh': r.get('abstract_zh', '')[:200] + '...' if len(r.get('abstract_zh', '')) > 200 else r.get('abstract_zh', '')  # 限制长度
                    })
            result['results'] = simplified_results

    # 清理返回数据，防止 JSON 解析错误
    return sanitize_tool_response(result)


# --- 文献管理（仅在用户要求时使用）(1个) ---

@mcp.tool()
async def save_papers_to_csv(
    papers: List[Dict[str, Any]],
    output_path: str = None,
    output_dir: str = None
) -> Dict[str, Any]:
    """
    Save papers to CSV file.

    将论文信息导出为CSV格式，包含所有字段：
    - ID, Title, Authors, Abstract, URL, Published, Source, Categories, Score等

    Args:
        papers: List of paper dictionaries containing:
            - id/arxiv_id/paper_id: Paper ID
            - title: Paper title
            - authors: Author list
            - abstract/summary: Abstract
            - url/pdf_url: Download URL
            - published: Publication date
            - source: Source (arxiv, tavily, etc.)
            - categories: Categories (optional)
            - score: Relevance score (optional)
        output_path: Full path to output file (optional)
        output_dir: Directory to save file (optional, default: ./output)

    Returns:
        Dict with status and CSV content
    """
    return save_papers_to_csv_impl(
        papers=papers,
        output_path=output_path,
        output_dir=output_dir,
        session_id=None
    )


# ============================================================================
# Report Generator Agent 工具 (1个)
# ============================================================================
# 职责：根据论文总结和全文生成研究报告（返回内容，不保存文件）

@mcp.tool()
async def generate_research_report(
    topic: str,
    csv_file_path: str = None,
    papers_info: List[Dict[str, Any]] = None,
    papers_analysis: List[Dict[str, Any]] = None,
    session_id: str = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive research report based on multiple papers.

    根据论文信息生成研究报告，并保存到 Markdown 文件和 CSV 文件。

    This tool creates a detailed scientific research report including:
    - Executive Summary（执行摘要）
    - Background（背景介绍）
    - Current Status（研究现状）
    - Existing Methods（现有方法）
    - Detailed Analysis（详细分析）
    - Open Problems（开放问题）
    - Potential Solutions（潜在解决方案）
    - Future Outlook（未来展望）
    - References（参考文献，IEEE 格式）

    Args:
        topic: The research topic/theme for the report
        csv_file_path: CSV文件路径（优先使用，从CSV读取论文信息）
        papers_info: 论文信息列表（如果未提供csv_file_path，则使用此参数）
        papers_analysis: 论文分析列表（可选）
        session_id: 会话ID（用于确定保存位置，可选）

    Returns:
        Dict containing the report content and metadata:
        - status: "success" or "error"
        - report: Markdown formatted report text
        - topic: Research topic
        - papers_count: Number of papers analyzed
        - report_file_path: 报告文件路径（MD格式）
        - csv_file_path: CSV文件路径
        - md_download_url: MD文件下载链接
        - csv_download_url: CSV文件下载链接
    """
    from modules.paper_manager.export_tools import save_report_to_file, save_report_papers_to_csv, read_papers_from_csv

    # 优先使用CSV文件
    if csv_file_path:
        logger.info(f"Reading papers from CSV: {csv_file_path}")
        papers_info = read_papers_from_csv(csv_file_path)
        if not papers_info:
            return {
                'status': 'error',
                'error': f'Failed to read papers from CSV: {csv_file_path}'
            }

        # 从CSV文件路径中提取session_id
        # 路径格式: papers/{session_id}/xxx.csv
        # 注意: generate_research_report已经有topic参数,所以不需要提取topic
        if not session_id:
            from pathlib import Path
            csv_path = Path(csv_file_path)
            # 获取倒数第二个路径部分(session_id所在的文件夹名)
            if len(csv_path.parts) >= 2:
                session_id = csv_path.parts[-2]
                logger.info(f"Extracted session_id from CSV path: {session_id}")
    elif not papers_info:
        return {
            'status': 'error',
            'error': 'Must provide either csv_file_path or papers_info'
        }

    # 如果没有 session_id，从 papers_info 中提取或使用 topic 生成
    if not session_id:
        # 尝试从 papers_info 中提取 session_id（如果论文是从搜索结果来的）
        # 检查 session_metadata.json 所在的文件夹
        import json
        from pathlib import Path

        # 尝试从第一篇论文的 paper_id 推断 session_id
        if papers_info and len(papers_info) > 0:
            first_paper_id = papers_info[0].get('paper_id') or papers_info[0].get('id')
            logger.info(f"Searching for session_id using paper_id: {first_paper_id}")
            if first_paper_id:
                # 查找包含这篇论文的 papers_info.json
                # 使用绝对路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                papers_dir = Path(current_dir) / 'papers'
                logger.info(f"Searching in papers directory: {papers_dir}")

                if papers_dir.exists():
                    for session_folder in papers_dir.iterdir():
                        if session_folder.is_dir():
                            # 优先读取 session_metadata.json
                            metadata_file = session_folder / 'session_metadata.json'
                            if metadata_file.exists():
                                try:
                                    with open(metadata_file, 'r', encoding='utf-8') as f:
                                        metadata = json.load(f)
                                        # 检查这个 session 是否包含我们的论文
                                        papers_info_file = session_folder / 'papers_info.json'
                                        if papers_info_file.exists():
                                            with open(papers_info_file, 'r', encoding='utf-8') as pf:
                                                papers_data = json.load(pf)
                                                if first_paper_id in papers_data:
                                                    session_id = metadata.get('session_id')
                                                    logger.info(f"Found existing session_id from metadata: {session_id} in folder: {session_folder.name}")

                                                    # 重要：从 papers_info.json 中加载所有论文（包括 Tavily）
                                                    # 如果用户传入的 papers_info 列表不完整，补充完整
                                                    all_papers_from_file = list(papers_data.values())
                                                    if len(all_papers_from_file) > len(papers_info):
                                                        logger.info(f"Found {len(all_papers_from_file)} papers in papers_info.json, but only {len(papers_info)} were provided. Using all papers from file.")

                                                        # 清理和标准化论文数据
                                                        cleaned_papers = []
                                                        for paper in all_papers_from_file:
                                                            cleaned_paper = {
                                                                'paper_id': paper.get('paper_id', ''),
                                                                'id': paper.get('id', ''),
                                                                'title': paper.get('title', '')[:500],  # 限制长度
                                                                'authors': paper.get('authors', []),
                                                                'abstract': paper.get('abstract', paper.get('content', ''))[:2000],  # 限制长度
                                                                'url': paper.get('url', ''),
                                                                'published': paper.get('published', ''),
                                                                'source': paper.get('source', ''),
                                                            }
                                                            cleaned_papers.append(cleaned_paper)

                                                        papers_info = cleaned_papers

                                                    break
                                except Exception as e:
                                    logger.error(f"Error reading metadata from {session_folder}: {e}")

        # 如果还是没有 session_id，使用 topic 生成一个唯一的
        if not session_id and topic:
            import uuid

            # 使用 topic + UUID 生成唯一的 session_id
            topic_clean = topic.lower().replace(' ', '_').replace('-', '_')
            unique_id = str(uuid.uuid4())[:8]  # 使用UUID的前8位确保唯一性

            # 限制session_id长度为50字符,避免路径过长
            if len(topic_clean) > 30:
                # 如果topic太长,只使用部分topic + unique_id
                session_id = f"{topic_clean[:30]}_{unique_id}"
            else:
                session_id = f"{topic_clean}_{unique_id}"

            logger.info(f"Generated unique session_id from topic: {session_id}")
        elif not session_id:
            # 如果都没有，生成一个随机的 session_id
            import uuid
            session_id = str(uuid.uuid4())[:8]
            logger.info(f"Generated random session_id: {session_id}")

    try:
        result = await generate_research_report_with_data_collection(
            papers_info=papers_info,
            topic=topic,
            papers_analysis=papers_analysis
        )

        # 保存报告到 Markdown 文件
        if result.get('status') == 'success':
            report_result = save_report_to_file(
                report_result=result,
                session_id=session_id,
                topic=topic
            )
            if report_result.get('file_path'):
                file_path = report_result['file_path']
                result['report_file_path'] = file_path
                # 添加下载URL
                # 规范化路径：移除 ./ 前缀，转换反斜杠为正斜杠
                file_path = file_path.replace('\\', '/').lstrip('./')
                if file_path.startswith('mcp_servers/paper_search/'):
                    file_path = file_path[len('mcp_servers/paper_search/'):]
                elif file_path.startswith('paper_search/'):
                    file_path = file_path[len('paper_search/'):]
                # 使用新的 get_download_url 函数生成下载URL
                result['md_download_url'] = get_download_url(file_path)

            # 保存论文信息到 CSV 文件（使用专门的报告论文保存函数）
            try:
                csv_result = save_report_papers_to_csv(
                    papers=papers_info,
                    session_id=session_id,
                    topic=topic,
                    file_prefix='report_papers'
                )
                
                if csv_result.get('status') == 'success' and csv_result.get('file_path'):
                    file_path = csv_result['file_path']
                    result['csv_file_path'] = file_path
                    # 使用新的 get_download_url 函数生成下载URL
                    result['csv_download_url'] = get_download_url(file_path)
                    logger.info(f"✅ CSV file saved and download URL generated: {result['csv_download_url']}")
                else:
                    logger.warning(f"⚠️ CSV save failed or no file path: {csv_result}")
                    
            except Exception as csv_error:
                logger.error(f"❌ Failed to save CSV file: {csv_error}")
                # 不让CSV保存失败影响整个报告生成
                result['csv_error'] = str(csv_error)

            # 删除完整的report内容,只保留摘要
            if 'report' in result:
                report_content = result['report']
                # 只保留前500个字符作为摘要
                result['report_summary'] = report_content[:500] + '...' if len(report_content) > 500 else report_content
                del result['report']

        # 清理返回数据，防止 JSON 解析错误
        return sanitize_tool_response(result)

    except Exception as e:
        logger.error(f'Failed to generate research report: {str(e)}')
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# Context Manager Agent 工具 (4个)
# ============================================================================
# 职责：向量化存储、语义搜索、Embedding、缓存管理

# --- 向量化和语义搜索 (2个) ---

@mcp.tool()
async def ingest_papers_to_vector_store(
    paper_ids: List[str],
    collection_name: str = "papers",
    source_type: str = "arxiv"
) -> Dict[str, Any]:
    """
    Ingest papers into vector store for semantic search.

    将论文内容向量化存储到 ChromaDB，支持多源文献和多collection。

    Args:
        paper_ids: List of paper IDs to ingest
        collection_name: Name of the collection to store papers in (default: "papers")
        source_type: Source type - "arxiv", "tavily", etc. (default: "arxiv")

    Returns:
        Dict with status and ingestion results:
        - status: "success" or "error"
        - collection_name: Collection name
        - ingested_documents: Number of papers ingested
        - failed_documents: List of failed papers
    """
    try:
        session_id = None

        # Get vector store and embedding service
        vector_store = get_vector_store(session_id=session_id)
        embedding_service = get_embedding_service()

        # Define content fetcher based on source type
        if source_type == "arxiv":
            content_fetcher = get_arxiv_paper_content_impl
        else:
            # For other sources, use a generic fetcher
            def generic_fetcher(paper_id):
                return {
                    'status': 'error',
                    'error': f'Content fetching not implemented for source: {source_type}'
                }
            content_fetcher = generic_fetcher

        # Ingest papers (use internal implementation function)
        result = await ingest_papers_impl(
            paper_ids=paper_ids,
            collection_name=collection_name,
            vector_store=vector_store,
            embedding_service=embedding_service,
            get_paper_content_func=content_fetcher
        )

        return result

    except Exception as e:
        logger.error(f'Failed to ingest papers: {str(e)}')
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@mcp.tool()
async def semantic_search_papers(
    query: str,
    top_k: int = 5,
    collection_name: str = "papers",
    filter_source: str = None
) -> List[Dict[str, Any]]:
    """
    Perform semantic search on ingested papers.

    基于向量相似度进行语义搜索，支持按来源过滤。

    Args:
        query: Search query (自然语言查询)
        top_k: Number of results to return (default: 5)
        collection_name: Name of the collection to search (default: "papers")
        filter_source: Optional source filter - "arxiv", "tavily", etc.

    Returns:
        List of search results with paper content and metadata
    """
    logger.info("Performing semantic search", query=query, top_k=top_k, collection_name=collection_name)

    try:
        session_id = None

        # Get vector store and embedding service
        vector_store = get_vector_store(session_id=session_id)
        embedding_service = get_embedding_service()

        # Get query embedding
        query_embedding = await embedding_service.embed_query(query)

        # Prepare filter
        metadata_filter = None
        if filter_source:
            metadata_filter = {"source_type": filter_source}

        # Search in vector store
        results = vector_store.search(
            query_embedding=query_embedding,
            collection_name=collection_name,
            top_k=top_k,
            filter=metadata_filter
        )

        return results

    except Exception as e:
        logger.error(f'Semantic search failed: {str(e)}')
        return []


# ============================================================================
# 工具优化完成 - 17 个核心工具
# ============================================================================
# 1. 规划类 (1个): generate_research_plan
# 2. 检索类 (8个):
#    - search_papers_all_sources (推荐：默认使用综合检索)
#    - search_arxiv_papers, search_papers_by_author, get_paper_info
#    - tavily_search, tavily_academic_search, tavily_news_search
# 3. 文献下载 (1个): download_paper
# 4. 内容获取 (2个): fetch_paper_content_from_url, get_paper_content
# 5. 批量汇总 (1个): batch_paper_analysis
# 6. 导出工具 (1个): save_papers_to_csv
# 7. 获取全文生成报告 (1个): generate_research_report
# 8. 向量化工具 (2个): ingest_papers_to_vector_store, semantic_search_papers
# ============================================================================
# 新增功能：
# - ✅ 统一字段命名（paper_id, abstract, url等）
# - ✅ CSV导出支持所有字段
# - ✅ 向量存储支持多collection和多源文献
# - ✅ 语义搜索支持按来源过滤
# - ✅ LLM翻译摘要
# - ✅ 通用URL全文提取（PDF和HTML）
# - ✅ 失败时自动回退到摘要
# ============================================================================


if __name__ == "__main__":
    # Parse arguments
    args = parse_args()

    # Configure logging to stderr (IMPORTANT: stdout is reserved for JSON-RPC messages in STDIO transport)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr  # Output to stderr instead of stdout
    )

    # Configure structlog to output to stderr
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),  # Output to stderr
        cache_logger_on_first_use=True,
    )

    logger.info("Starting Paper Search MCP Server V9.0.0")
    logger.info(f"Server will run on {args.host}:{args.port}")
    logger.info("V9.0 Features: Reorganized tools by agent responsibilities")
    logger.info("Available tools:")
    logger.info("  - Search Agent: 7 tools (Planning: 1, ArXiv: 3, Tavily: 3)")
    logger.info("  - Paper Manager: 5 tools (Get Content: 2, Analysis: 2, Save: 1)")
    logger.info("  - Report Generator: 1 tool (Generate Report)")
    logger.info("  - Context Manager: 4 tools (Vector: 2, Cache: 2)")
    logger.info("  - Shared: 1 tool (Health Check)")
    logger.info(f"Tavily: {'Available' if is_tavily_available() else 'Not installed'}")
    logger.info("🆕 New: Tools reorganized by agent responsibilities")
    logger.info("🆕 Removed: Duplicate tool definitions and Google Scholar")
    logger.info("🆕 Focus: Each agent has clear responsibilities")

    import warnings

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Suppress deprecation warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # Run in SSE mode
    import uvicorn
    # Get configuration from environment
    host = os.getenv("PAPER_SEARCH_MCP_HOST", "127.0.0.1")  # Bind to localhost by default
    port = int(os.getenv("PAPER_SEARCH_MCP_PORT", "50004"))
    external_url = os.getenv("PAPER_SEARCH_MCP_URL", f"http://127.0.0.1:{port}/sse")

    logger.info(f"[START] Starting Paper Search MCP Server in SSE mode on http://{host}:{port}")
    logger.info("[INFO] Using SSE transport")
    logger.info(f"[INFO] External URL: {external_url}")
    logger.info(f"[INFO] Internal Endpoint: http://{host}:{port}/sse")

    # Create HTTP app
    http_app = mcp.http_app(transport="sse")
    
    # Add health check route using Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    
    async def health_check(request):
        """Health check endpoint for paper search MCP server"""
        return JSONResponse({
            "status": "healthy",
            "service": "paper_search_mcp",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "tavily_available": is_tavily_available()
        })
    
    # Add health route to existing routes
    health_route = Route("/health", health_check, methods=["GET"])
    http_app.router.routes.append(health_route)
    
    # Use SSE transport explicitly
    uvicorn.run(
        http_app,
        host=host,
        port=port,
        log_level="info",
        reload=False,
        timeout_keep_alive=300,
        limit_concurrency=100,
        backlog=2048
    )
