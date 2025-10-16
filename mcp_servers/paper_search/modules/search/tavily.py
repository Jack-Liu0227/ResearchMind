"""
Tavily Web Search Module (Tavily 网页搜索模块)

功能：
1. 通用网页搜索
2. 学术网页搜索
3. 新闻搜索
"""
import os
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)

# 尝试导入 Tavily
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logger.warning("⚠️ Tavily not installed. Web search will not be available.")
    logger.warning("Install with: pip install tavily-python")


def is_tavily_available() -> bool:
    """Check if Tavily is available"""
    return TAVILY_AVAILABLE


async def search_web(query: str, max_results: int = 5, search_depth: str = "basic", session_id: str = None) -> List[Dict[str, Any]]:
    """
    Perform general web search using Tavily.

    Args:
        query: Search query
        max_results: Maximum number of results (default: 5)
        search_depth: Search depth - "basic" or "advanced" (default: "basic")
        session_id: Optional session ID for session-level storage

    Returns:
        List of search results with title, url, content, and score (直接返回结果列表)
    """
    if not TAVILY_AVAILABLE:
        return [{
            "error": "Tavily not installed",
            "message": "Install with: pip install tavily-python"
        }]

    try:
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            return [{
                "error": "TAVILY_API_KEY not set",
                "message": "Please set TAVILY_API_KEY environment variable"
            }]

        client = TavilyClient(api_key=api_key)

        response = client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=True,
            include_raw_content=False
        )

        results = []
        for item in response.get('results', []):
            # Generate paper_id from URL
            import hashlib
            url = item.get('url', '')
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

            # Unified field format
            result = {
                'paper_id': f"tavily_{url_hash}",  # 统一主键
                'id': f"tavily_{url_hash}",
                'title': item.get('title', ''),
                'authors': [],  # Tavily通常不提供作者信息
                'abstract': item.get('content', ''),  # 统一使用abstract
                'summary': item.get('content', ''),  # 保留兼容性
                'url': url,  # 统一使用url
                'pdf_url': '',  # Tavily通常不提供PDF链接
                'published': item.get('published_date', ''),
                'published_date': item.get('published_date', ''),
                'categories': [],
                'source': 'tavily',
                'doi': '',  # 尝试从URL提取
                'score': item.get('score', 0.0),
                # 额外字段
                'content': item.get('content', ''),
            }

            # Try to extract DOI from URL
            if 'doi.org/' in url:
                result['doi'] = url.split('doi.org/')[-1]

            results.append(result)

        logger.info(f"Web search completed: {len(results)} results for '{query}'", session_id=session_id)

        # 保存结果到 papers_info.json（与 ArXiv 结果合并）
        if results and session_id:
            _save_tavily_results_to_file(results, query, session_id)

        # 直接返回结果列表
        return results

    except Exception as e:
        logger.error(f"Web search failed: {str(e)}")
        return [{
            "error": f"Search failed: {str(e)}"
        }]


async def search_academic_web(query: str, max_results: int = 5, session_id: str = None) -> List[Dict[str, Any]]:
    """
    Perform academic-focused web search using Tavily.

    Args:
        query: Search query
        max_results: Maximum number of results (default: 5)
        session_id: Optional session ID for session-level storage

    Returns:
        List of academic search results (直接返回结果列表，不包装在字典中)
    """
    if not TAVILY_AVAILABLE:
        return [{
            "error": "Tavily not installed",
            "message": "Install with: pip install tavily-python"
        }]

    try:
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            return [{
                "error": "TAVILY_API_KEY not set",
                "message": "Please set TAVILY_API_KEY environment variable"
            }]

        client = TavilyClient(api_key=api_key)

        # Add academic keywords to query
        academic_query = f"{query} academic research paper"

        response = client.search(
            query=academic_query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
            include_domains=["arxiv.org", "scholar.google.com", "ieee.org", "acm.org", "springer.com", "sciencedirect.com"]
        )

        results = []
        for item in response.get('results', []):
            # Generate paper_id from URL
            import hashlib
            url = item.get('url', '')
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

            # Unified field format
            result = {
                'paper_id': f"tavily_academic_{url_hash}",  # 统一主键
                'id': f"tavily_academic_{url_hash}",
                'title': item.get('title', ''),
                'authors': [],  # Tavily通常不提供作者信息
                'abstract': item.get('content', ''),  # 统一使用abstract
                'summary': item.get('content', ''),  # 保留兼容性
                'url': url,  # 统一使用url
                'pdf_url': '',  # Tavily通常不提供PDF链接
                'published': item.get('published_date', ''),
                'published_date': item.get('published_date', ''),
                'categories': [],
                'source': 'tavily_academic',
                'doi': '',  # 尝试从URL提取
                'score': item.get('score', 0.0),
                # 额外字段
                'content': item.get('content', ''),
            }

            # Try to extract DOI from URL
            if 'doi.org/' in url:
                result['doi'] = url.split('doi.org/')[-1]

            results.append(result)

        logger.info(f"Academic web search completed: {len(results)} results for '{query}'", session_id=session_id)

        # 保存结果到 papers_info.json（与 ArXiv 结果合并）
        if results and session_id:
            _save_tavily_results_to_file(results, query, session_id)

        # 直接返回结果列表，不包装在字典中
        return results

    except Exception as e:
        logger.error(f"Academic web search failed: {str(e)}")
        return [{
            "error": f"Search failed: {str(e)}"
        }]


def _save_tavily_results_to_file(results: List[Dict[str, Any]], query: str, session_id: str):
    """
    Save Tavily search results to papers_info.json (merge with ArXiv results).

    Args:
        results: List of Tavily search results
        query: Search query (used for folder name)
        session_id: Session ID
    """
    try:
        import json
        from pathlib import Path
        from ..shared.session_folder_manager import get_session_folder

        # Get session folder
        path = get_session_folder(session_id, query)
        file_path = Path(path) / "papers_info.json"

        # Load existing papers info
        papers_info = {}
        if file_path.exists():
            try:
                with open(file_path, "r", encoding='utf-8') as json_file:
                    papers_info = json.load(json_file)
            except (FileNotFoundError, json.JSONDecodeError):
                papers_info = {}

        # Add Tavily results
        for result in results:
            # Use URL as unique ID for Tavily results
            paper_id = f"tavily_{result.get('url', '').replace('/', '_').replace(':', '_')[:50]}"

            papers_info[paper_id] = {
                'paper_id': paper_id,
                'title': result.get('title', ''),
                'url': result.get('url', ''),
                'content': result.get('content', ''),
                'score': result.get('score', 0.0),
                'published_date': result.get('published_date', ''),
                'source': 'tavily'
            }

        # Save merged results
        with open(file_path, "w", encoding='utf-8') as json_file:
            json.dump(papers_info, json_file, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(results)} Tavily results to {file_path}", session_id=session_id)

    except Exception as e:
        logger.error(f"Failed to save Tavily results: {str(e)}", session_id=session_id)


async def search_news(query: str, max_results: int = 5, days: int = 7) -> List[Dict[str, Any]]:
    """
    Search for recent news articles using Tavily.

    Args:
        query: Search query
        max_results: Maximum number of results (default: 5)
        days: Number of days to look back (default: 7)

    Returns:
        List of news articles (直接返回结果列表)
    """
    if not TAVILY_AVAILABLE:
        return [{
            "error": "Tavily not installed",
            "message": "Install with: pip install tavily-python"
        }]

    try:
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            return [{
                "error": "TAVILY_API_KEY not set",
                "message": "Please set TAVILY_API_KEY environment variable"
            }]

        client = TavilyClient(api_key=api_key)

        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_answer=False,
            days=days
        )

        results = []
        for item in response.get('results', []):
            # Generate paper_id from URL
            import hashlib
            url = item.get('url', '')
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

            # Unified field format
            result = {
                'paper_id': f"tavily_news_{url_hash}",  # 统一主键
                'id': f"tavily_news_{url_hash}",
                'title': item.get('title', ''),
                'authors': [],  # News通常不提供作者信息
                'abstract': item.get('content', ''),  # 统一使用abstract
                'summary': item.get('content', ''),  # 保留兼容性
                'url': url,  # 统一使用url
                'pdf_url': '',
                'published': item.get('published_date', ''),
                'published_date': item.get('published_date', ''),
                'categories': [],
                'source': 'tavily_news',
                'doi': '',
                'score': item.get('score', 0.0),
                # 额外字段
                'content': item.get('content', ''),
            }
            results.append(result)

        logger.info(f"News search completed: {len(results)} results for '{query}'")

        # 直接返回结果列表
        return results

    except Exception as e:
        logger.error(f"News search failed: {str(e)}")
        return [{
            "error": f"Search failed: {str(e)}"
        }]

