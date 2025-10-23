"""
Unified Tools Module (统一工具模块)

提供统一的接口用于：
1. 搜索文献（多源）
2. 获取文献信息
3. 下载文献
4. 获取全文内容
"""
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union
import structlog

logger = structlog.get_logger(__name__)

SearchResultList = List[Dict[str, Any]]
SyncSearchHandler = Callable[[str, int, Optional[str]], Union[SearchResultList, Dict[str, Any]]]
AsyncSearchHandler = Callable[[str, int, Optional[str]], Awaitable[Union[SearchResultList, Dict[str, Any]]]]

SOURCE_REGISTRY: Dict[str, Dict[str, Any]] = {}
DEFAULT_SOURCES = ['arxiv', 'tavily_academic']


def register_search_source(
    name: str,
    handler: Union[SyncSearchHandler, AsyncSearchHandler],
    *,
    is_async: bool,
    description: str = ''
) -> None:
    """
    Register a search source so unified search can call it.

    Args:
        name: Unique identifier for the source (e.g., 'arxiv')
        handler: Callable that accepts (query, max_results, session_id)
        is_async: True if handler is awaitable, False if synchronous
        description: Optional human readable description
    """
    if not callable(handler):
        raise ValueError(f"Handler for source '{name}' must be callable")

    SOURCE_REGISTRY[name] = {
        'handler': handler,
        'is_async': is_async,
        'description': description or name
    }


def get_registered_sources() -> Dict[str, Dict[str, Any]]:
    """Return a copy of the registered sources."""
    return dict(SOURCE_REGISTRY)


def _ensure_default_sources() -> None:
    """
    Lazily register the built-in sources. This keeps the file extensible while
    avoiding heavy imports unless search is executed.
    """
    if 'arxiv' not in SOURCE_REGISTRY:
        from .search.arxiv import search_arxiv_papers

        register_search_source(
            'arxiv',
            search_arxiv_papers,
            is_async=False,
            description='ArXiv preprint archive'
        )

    if 'tavily_academic' not in SOURCE_REGISTRY:
        from .search.tavily import search_academic_web

        register_search_source(
            'tavily_academic',
            search_academic_web,
            is_async=True,
            description='Tavily academic web search'
        )

    if 'tavily' not in SOURCE_REGISTRY:
        from .search.tavily import search_web

        register_search_source(
            'tavily',
            search_web,
            is_async=True,
            description='Tavily general web search'
        )


# ============================================================================
# 统一搜索接口
# ============================================================================

async def search_papers(
    query: str,
    sources: List[str] = None,
    max_results: int = 3,
    session_id: str = None
) -> Dict[str, Any]:
    """
    统一的文献搜索接口（异步并行执行）

    Args:
        query: 搜索查询
        sources: 搜索源列表 ['arxiv', 'tavily', 'tavily_academic']
                如果为None，则搜索所有源
        max_results: 每个源的最大结果数
        session_id: 会话ID（用于保存搜索结果到文件）

    Returns:
        Dict containing:
        - papers: 统一格式的论文列表
        - sources_used: 使用的搜索源
        - total_results: 总结果数
    """
    import asyncio
    from .shared.field_mapping import merge_paper_data

    # Register built-in sources on demand so the registry stays extensible.
    _ensure_default_sources()

    # 默认搜索所有源
    if sources is None:
        sources = [src for src in DEFAULT_SOURCES if src in SOURCE_REGISTRY]
    else:
        seen = set()
        sources = [src for src in sources if not (src in seen or seen.add(src))]

    # 过滤掉未知的源但保留日志，方便未来扩展
    unknown_sources = [src for src in sources if src not in SOURCE_REGISTRY]
    if unknown_sources:
        logger.warning(
            "Requested sources are not registered and will be skipped",
            unknown_sources=unknown_sources,
            available=list(SOURCE_REGISTRY.keys())
        )
    sources = [src for src in sources if src in SOURCE_REGISTRY]
    if not sources:
        return {
            'status': 'error',
            'error': 'No valid sources available',
            'message': 'Requested sources are not registered.'
        }

    # 规范化 max_results
    try:
        max_results_value = int(max_results)
    except (TypeError, ValueError):
        logger.warning("Invalid max_results provided to search_papers, falling back to default", requested=max_results)
        max_results_value = 3

    if max_results_value < 1:
        max_results_value = 1
    elif max_results_value > 50:
        logger.info("Clamping max_results to 50 for unified search", requested=max_results_value)
        max_results_value = 50

    max_results = max_results_value

    try:
        # 异步搜索单个源
        async def search_source(source_name: str) -> tuple:
            """异步搜索单个源"""
            try:
                config = SOURCE_REGISTRY.get(source_name)
                if not config:
                    logger.warning("Search source is not registered", source=source_name)
                    return (source_name, [])

                handler = config['handler']
                is_async_handler = config['is_async']

                if is_async_handler:
                    results = await handler(query, max_results=max_results, session_id=session_id)
                else:
                    loop = asyncio.get_running_loop()
                    results = await loop.run_in_executor(
                        None,
                        lambda: handler(query, max_results=max_results, session_id=session_id)
                    )

                # handler could return dict or list; normalize to list
                if isinstance(results, dict):
                    if results.get('status') == 'success':
                        papers = results.get('papers', [])
                    else:
                        logger.warning(
                            "Search source returned an error response",
                            source=source_name,
                            response=results
                        )
                        papers = []
                else:
                    papers = results

                logger.info(
                    "Search source completed",
                    source=source_name,
                    results=len(papers),
                    description=config.get('description', source_name)
                )
                return (source_name, papers)

            except Exception as e:
                logger.error(f"Search failed for {source_name}: {e}")
                return (source_name, [])

        # 并行执行所有源的搜索
        logger.info(
            "Executing parallel paper search",
            source_count=len(sources),
            max_results=max_results,
            query=query
        )

        search_tasks = [search_source(source_name) for source_name in sources]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # 处理结果
        all_papers = []
        sources_used = []
        for result in search_results:
            if isinstance(result, Exception):
                logger.error("Search task failed with exception", error=str(result))
                continue

            source_name, papers = result
            if papers:
                all_papers.append(papers)
                sources_used.append(source_name)

        # 合并并去重
        merged_papers = merge_paper_data(all_papers)

        return {
            'status': 'success',
            'papers': merged_papers,
            'sources_used': sources_used,
            'total_results': len(merged_papers),
            'message': f'Found {len(merged_papers)} papers from {len(sources_used)} sources'
        }
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'papers': [],
            'sources_used': sources_used
        }


# ============================================================================
# 统一内容获取接口
# ============================================================================

def get_paper_content(
    paper: Dict[str, Any],
    prefer_fulltext: bool = True
) -> Dict[str, Any]:
    """
    统一的文献内容获取接口
    
    Args:
        paper: 论文信息字典（包含paper_id, source, url等）
        prefer_fulltext: 是否优先获取全文（否则只返回摘要）
    
    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - content: 文本内容
        - metadata: 元数据（source_type, fallback等）
    """
    from .paper_manager.content_fetcher import get_paper_content_by_source
    
    try:
        paper_id = paper.get('paper_id', 'unknown')
        source = paper.get('source', 'unknown')
        
        if not prefer_fulltext:
            # 只返回摘要
            abstract = paper.get('abstract', '')
            return {
                'status': 'success',
                'content': abstract,
                'metadata': {
                    'source_type': 'abstract',
                    'fallback': False
                }
            }
        
        # 获取全文
        result = get_paper_content_by_source(paper, source)
        
        logger.info(f"Got content for {paper_id} from {source}")
        return result
    
    except Exception as e:
        logger.error(f"Failed to get content for {paper.get('paper_id', 'unknown')}: {e}")
        
        # 回退到摘要
        abstract = paper.get('abstract', '')
        return {
            'status': 'success',
            'content': abstract,
            'metadata': {
                'fallback': True,
                'fallback_reason': str(e)
            }
        }


# ============================================================================
# 统一下载接口
# ============================================================================

def download_paper_file(
    paper: Dict[str, Any],
    download_dir: str = None
) -> Dict[str, Any]:
    """
    统一的文献下载接口
    
    Args:
        paper: 论文信息字典
        download_dir: 下载目录
    
    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - file_path: 下载的文件路径
        - message: 消息
    """
    from .search.arxiv import download_paper as download_arxiv_paper
    import requests
    import os
    from pathlib import Path
    
    try:
        paper_id = paper.get('paper_id', 'unknown')
        source = paper.get('source', 'unknown')
        
        # 设置下载目录
        if not download_dir:
            download_dir = './papers'
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        # ArXiv论文使用专用下载函数
        if source == 'arxiv':
            pdf_url = paper.get('pdf_url', '')
            if pdf_url:
                file_path = download_arxiv_paper(pdf_url, download_dir)
                return {
                    'status': 'success',
                    'file_path': file_path,
                    'message': f'Downloaded ArXiv paper to {file_path}'
                }
        
        # 其他源：尝试下载PDF
        pdf_url = paper.get('pdf_url') or paper.get('url')
        if pdf_url and pdf_url.endswith('.pdf'):
            response = requests.get(pdf_url, timeout=60)
            response.raise_for_status()
            
            # 生成文件名
            safe_title = "".join(c for c in paper.get('title', paper_id)[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
            file_name = f"{safe_title}.pdf"
            file_path = os.path.join(download_dir, file_name)
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return {
                'status': 'success',
                'file_path': file_path,
                'message': f'Downloaded paper to {file_path}'
            }
        
        return {
            'status': 'error',
            'error': 'No PDF URL available',
            'message': 'Cannot download: no PDF URL found'
        }
    
    except Exception as e:
        logger.error(f"Download failed for {paper.get('paper_id', 'unknown')}: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'message': f'Download failed: {str(e)}'
        }


# ============================================================================
# 统一信息获取接口
# ============================================================================

def get_paper_info(
    paper_id: str,
    source: str = 'arxiv'
) -> Dict[str, Any]:
    """
    统一的文献信息获取接口
    
    Args:
        paper_id: 论文ID
        source: 来源（arxiv, tavily等）
    
    Returns:
        统一格式的论文信息字典
    """
    from .search.arxiv import get_paper_info as get_arxiv_info
    from .shared.field_mapping import normalize_paper_fields
    
    try:
        if source == 'arxiv':
            # 使用ArXiv API获取信息
            info = get_arxiv_info(paper_id)
            if info.get('status') == 'success':
                paper_data = info.get('paper', {})
                # 标准化字段
                return normalize_paper_fields(paper_data, 'arxiv')
        
        # 其他源暂不支持
        return {
            'status': 'error',
            'error': f'Source {source} not supported for get_paper_info'
        }
    
    except Exception as e:
        logger.error(f"Failed to get info for {paper_id}: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

