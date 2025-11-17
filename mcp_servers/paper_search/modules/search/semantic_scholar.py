"""
Semantic Scholar Search Module (Semantic Scholar 检索模块)

功能：
1. Semantic Scholar 论文搜索
2. 支持统一的论文格式
3. 异步搜索支持
"""
import os
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
import structlog
import hashlib

logger = structlog.get_logger(__name__)

# Semantic Scholar API 配置
SEMANTIC_SCHOLAR_API_BASE = "https://api.semanticscholar.org/graph/v1"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 2
RETRY_DELAY = 1


async def search_semantic_scholar_papers(
    query: str, 
    max_results: int = 5, 
    session_id: str = None
) -> List[Dict[str, Any]]:
    """
    使用 Semantic Scholar API 搜索论文（异步）
    
    Args:
        query: 搜索查询
        max_results: 最大结果数（默认：5）
        session_id: 会话ID（用于保存结果到文件）
    
    Returns:
        统一格式的论文列表
    """
    try:
        # 确保 max_results 是有效的正整数
        max_results = max(1, int(max_results))
        logger.info(
            "Starting Semantic Scholar search",
            query=query,
            max_results=max_results
        )
        
        # 获取 API Key
        api_key = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
        if not api_key:
            logger.warning("SEMANTIC_SCHOLAR_API_KEY not set, using unauthenticated access")
        
        # 构建请求 URL 和参数
        url = f"{SEMANTIC_SCHOLAR_API_BASE}/paper/search/bulk"
        
        # 请求的字段（与统一格式对应）
        fields = "paperId,title,authors,abstract,url,publicationDate,citationCount,publicationTypes,externalIds,openAccessPdf,fieldsOfStudy"
        
        params = {
            "query": query,
            "fields": fields,
            "limit": min(max_results, 100)  # API 限制每次最多 100 条
        }
        
        # 设置请求头
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key
        
        # 发送请求
        all_papers = []
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                params=params, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # 提取论文数据
                papers_data = data.get('data', [])
                
                # 转换为统一格式
                for paper in papers_data[:max_results]:
                    normalized_paper = _normalize_semantic_scholar_paper(paper)
                    all_papers.append(normalized_paper)
        
        logger.info(
            "Semantic Scholar search completed",
            query=query,
            requested_max_results=max_results,
            actual_results=len(all_papers)
        )
        
        # 保存结果到 papers_info.json（与其他源合并）
        if all_papers and session_id:
            _save_semantic_scholar_results_to_file(all_papers, query, session_id)
        
        return all_papers
    
    except aiohttp.ClientError as e:
        logger.error(f"Semantic Scholar API request failed: {str(e)}")
        return [{
            "error": f"API request failed: {str(e)}"
        }]
    except Exception as e:
        logger.error(f"Semantic Scholar search failed: {str(e)}")
        return [{
            "error": f"Search failed: {str(e)}"
        }]


def _normalize_semantic_scholar_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 Semantic Scholar 论文数据转换为统一格式
    
    Args:
        paper: Semantic Scholar API 返回的原始论文数据
    
    Returns:
        统一格式的论文字典
    """
    # 提取 paper_id
    paper_id = paper.get('paperId', '')
    
    # 提取作者列表
    authors = []
    for author in paper.get('authors', []):
        author_name = author.get('name', '')
        if author_name:
            authors.append(author_name)
    
    # 提取 DOI
    doi = ''
    external_ids = paper.get('externalIds', {})
    if external_ids:
        doi = external_ids.get('DOI', '') or external_ids.get('ArXiv', '')
    
    # 提取 PDF URL
    pdf_url = ''
    open_access_pdf = paper.get('openAccessPdf')
    if open_access_pdf and isinstance(open_access_pdf, dict):
        pdf_url = open_access_pdf.get('url', '')

    # 提取分类
    categories = paper.get('fieldsOfStudy', []) or []

    # 提取发表日期
    published_date = paper.get('publicationDate', '')

    # 提取 URL（使用 Semantic Scholar 页面）
    url = paper.get('url', '')
    if not url and paper_id:
        url = f"https://www.semanticscholar.org/paper/{paper_id}"

    # 统一字段格式
    normalized = {
        'paper_id': f"s2_{paper_id}",  # 统一主键，添加前缀避免与其他源冲突
        'id': paper_id,  # Semantic Scholar Paper ID
        'title': paper.get('title', ''),
        'authors': authors,
        'abstract': paper.get('abstract', ''),  # 统一使用 abstract
        'summary': paper.get('abstract', ''),  # 保留兼容性
        'url': url,  # 统一使用 url
        'pdf_url': pdf_url,
        'published': published_date,
        'published_date': published_date,
        'categories': categories,
        'source': 'semantic_scholar',
        'doi': doi,
        # 额外字段
        'citation_count': paper.get('citationCount', 0),
        'publication_types': paper.get('publicationTypes', []),
        'external_ids': external_ids,
    }

    return normalized


def _save_semantic_scholar_results_to_file(
    results: List[Dict[str, Any]],
    query: str,
    session_id: str
):
    """
    保存 Semantic Scholar 搜索结果到 papers_info.json（与其他源合并）

    Args:
        results: Semantic Scholar 搜索结果列表
        query: 搜索查询（用于文件夹名称）
        session_id: 会话ID
    """
    try:
        import json
        from pathlib import Path
        from ..shared.session_folder_manager import get_session_folder

        # 获取会话文件夹
        path = get_session_folder(session_id, query)
        file_path = Path(path) / "papers_info.json"

        # 加载现有的论文信息
        papers_info = {}
        if file_path.exists():
            try:
                with open(file_path, "r", encoding='utf-8') as json_file:
                    papers_info = json.load(json_file)
            except (FileNotFoundError, json.JSONDecodeError):
                papers_info = {}

        # 添加 Semantic Scholar 结果
        for result in results:
            paper_id = result.get('paper_id', '')
            if paper_id:
                papers_info[paper_id] = result

        # 保存合并后的结果
        with open(file_path, "w", encoding='utf-8') as json_file:
            json.dump(papers_info, json_file, indent=2, ensure_ascii=False)

        logger.info(
            f"Saved {len(results)} Semantic Scholar results to {file_path}",
            session_id=session_id
        )

    except Exception as e:
        logger.error(
            f"Failed to save Semantic Scholar results: {str(e)}",
            session_id=session_id
        )

