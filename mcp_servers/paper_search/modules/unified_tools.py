"""
Unified Tools Module (统一工具模块)

提供统一的接口用于：
1. 搜索文献（多源）
2. 获取文献信息
3. 下载文献
4. 获取全文内容
"""
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger(__name__)


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
    统一的文献搜索接口

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
    from .search.arxiv import search_arxiv_papers
    from .search.tavily import search_web, search_academic_web
    from .shared.field_mapping import batch_normalize_papers, merge_paper_data
    
    # 默认搜索所有源
    if sources is None:
        sources = ['arxiv', 'tavily_academic']

    all_papers = []  # 存储每个源的论文列表
    sources_used = []

    try:
        # ArXiv搜索
        if 'arxiv' in sources:
            try:
                arxiv_results = search_arxiv_papers(query, max_results=max_results, session_id=session_id)
                # 检查返回值类型
                if isinstance(arxiv_results, dict) and arxiv_results.get('status') == 'success':
                    papers = arxiv_results.get('papers', [])
                    all_papers.append(papers)  # 添加整个列表
                    sources_used.append('arxiv')
                    logger.info(f"ArXiv search: {len(papers)} papers")
                elif isinstance(arxiv_results, list):
                    # 如果直接返回列表
                    all_papers.append(arxiv_results)  # 添加整个列表
                    sources_used.append('arxiv')
                    logger.info(f"ArXiv search: {len(arxiv_results)} papers")
            except Exception as e:
                logger.error(f"ArXiv search failed: {e}")

        # Tavily Academic搜索
        if 'tavily_academic' in sources:
            try:
                tavily_results = await search_academic_web(query, max_results=max_results, session_id=session_id)
                if isinstance(tavily_results, list):
                    all_papers.append(tavily_results)  # 添加整个列表
                    sources_used.append('tavily_academic')
                    logger.info(f"Tavily Academic search: {len(tavily_results)} papers")
            except Exception as e:
                logger.error(f"Tavily Academic search failed: {e}")

        # Tavily Web搜索
        if 'tavily' in sources:
            try:
                tavily_results = await search_web(query, max_results=max_results, session_id=session_id)
                if isinstance(tavily_results, list):
                    all_papers.append(tavily_results)  # 添加整个列表
                    sources_used.append('tavily')
                    logger.info(f"Tavily Web search: {len(tavily_results)} papers")
            except Exception as e:
                logger.error(f"Tavily Web search failed: {e}")

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

