"""
ArXiv Module (ArXiv 检索模块)

功能：
1. ArXiv 论文搜索
2. ArXiv 论文信息获取
3. ArXiv 论文内容提取（支持异步）
4. ArXiv 作者搜索
"""
import arxiv
import requests
import aiohttp
import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from io import BytesIO
from PyPDF2 import PdfReader
import structlog
import warnings
import time
import itertools

# Suppress PyPDF2 warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PyPDF2")

logger = structlog.get_logger(__name__)

# 超时配置
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 2
RETRY_DELAY = 1
ARXIV_MAX_RESULTS_LIMIT = 50

PAPER_DIR = "./paper_search/papers"


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符

    Windows非法字符: < > : " / \\ | ? *

    Args:
        filename: 原始文件名

    Returns:
        清理后的文件名
    """
    import re

    # 移除或替换Windows非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    clean_name = re.sub(illegal_chars, '_', filename)

    # 移除多余的下划线
    clean_name = re.sub(r'_+', '_', clean_name)

    # 移除首尾下划线和空格
    clean_name = clean_name.strip('_ ')

    # 限制长度（Windows路径限制）
    max_length = 200
    if len(clean_name) > max_length:
        clean_name = clean_name[:max_length]

    # 如果清理后为空，使用默认名称
    if not clean_name:
        clean_name = "unnamed"

    return clean_name


def _sanitize_max_results(value: Any) -> int:
    """
    Normalize the max_results argument to a safe, bounded positive integer.
    """
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        logger.warning("Invalid max_results value, falling back to default", requested=value)
        numeric = 5

    if numeric < 1:
        numeric = 1
    if numeric > ARXIV_MAX_RESULTS_LIMIT:
        logger.info(
            "Clamping max_results to upper bound",
            requested=numeric,
            limit=ARXIV_MAX_RESULTS_LIMIT
        )
        numeric = ARXIV_MAX_RESULTS_LIMIT

    return numeric


def search_arxiv_papers(topic: str, max_results: int = 5, session_id: str = None) -> List[Dict[str, Any]]:
    """
    Search for papers on arXiv based on a topic and store their information.

    Args:
        topic: The topic to search for
        max_results: Maximum number of results to retrieve (default: 5)

    Returns:
        List of dictionaries containing paper information (paper_id, title, authors, summary, etc.)
    """
    try:
        # 确保 max_results 是有效的正整数并限制在安全范围内
        max_results = _sanitize_max_results(max_results)
        logger.info(
            "Starting ArXiv search",
            topic=topic,
            max_results=max_results,
            limit=ARXIV_MAX_RESULTS_LIMIT
        )

        # Use arxiv to find the papers
        client = arxiv.Client()

        # Search for the most relevant articles matching the queried topic
        search = arxiv.Search(
            query=topic,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        # 获取结果并限制数量
        papers = list(itertools.islice(client.results(search), max_results))
        logger.info("ArXiv client returned results", requested=max_results, fetched=len(papers))

        # 使用会话文件夹管理器获取文件夹路径
        from ..shared.session_folder_manager import get_session_folder

        # 如果有 session_id，使用会话文件夹；否则创建临时会话
        if session_id:
            path = get_session_folder(session_id, topic)
        else:
            # 创建临时会话ID
            import uuid
            temp_session_id = str(uuid.uuid4())
            path = get_session_folder(temp_session_id, topic)
            logger.info(f"Created temporary session: {temp_session_id}")

        file_path = os.path.join(path, "papers_info.json")

        # Try to load existing papers info
        try:
            with open(file_path, "r", encoding='utf-8') as json_file:
                papers_info = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            papers_info = {}

        # Process each paper and add to papers_info
        paper_results = []
        for paper in papers:
            arxiv_id = paper.get_short_id()

            # Unified field format
            paper_info = {
                'paper_id': arxiv_id,  # 统一主键
                'id': arxiv_id,  # ArXiv ID
                'title': paper.title,
                'authors': [author.name for author in paper.authors],
                'abstract': paper.summary,  # 统一使用abstract
                'summary': paper.summary,  # 保留兼容性
                'url': paper.entry_id,  # 统一使用url
                'pdf_url': paper.pdf_url,
                'published': str(paper.published.date()),
                'categories': paper.categories,
                'source': 'arxiv',
                'doi': '',  # ArXiv通常没有DOI
                # 额外字段
                'entry_id': paper.entry_id,
                'updated': str(paper.updated.date()) if paper.updated else None,
            }
            papers_info[arxiv_id] = paper_info
            paper_results.append(paper_info)

        # Save updated papers_info to json file
        with open(file_path, "w", encoding='utf-8') as json_file:
            json.dump(papers_info, json_file, indent=2, ensure_ascii=False)

        logger.info(
            "ArXiv search completed",
            topic=topic,
            requested_max_results=max_results,
            actual_results=len(paper_results),
            file_path=file_path
        )
        return paper_results

    except Exception as e:
        logger.error("ArXiv search failed", topic=topic, error=str(e))
        return [f"Error: {str(e)}"]


def get_paper_info(paper_id: str) -> str:
    """
    Search for information about a specific paper across all topic directories.

    Args:
        paper_id: The ID of the paper to look for

    Returns:
        JSON string with paper information if found, error message if not found
    """
    try:
        if not os.path.exists(PAPER_DIR):
            return f"No papers directory found. Search for papers first."

        for item in os.listdir(PAPER_DIR):
            item_path = os.path.join(PAPER_DIR, item)
            if os.path.isdir(item_path):
                file_path = os.path.join(item_path, "papers_info.json")
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r", encoding='utf-8') as json_file:
                            papers_info = json.load(json_file)
                            if paper_id in papers_info:
                                logger.info("Paper info found", paper_id=paper_id)
                                return json.dumps(papers_info[paper_id], indent=2, ensure_ascii=False)
                    except (FileNotFoundError, json.JSONDecodeError) as e:
                        logger.warning(f"Error reading {file_path}: {str(e)}")
                        continue

        logger.warning("Paper not found", paper_id=paper_id)
        return f"No saved information found for paper {paper_id}. Try searching for papers first."

    except Exception as e:
        logger.error("Get paper info failed", paper_id=paper_id, error=str(e))
        return f"Error retrieving paper info: {str(e)}"


def list_saved_papers(topic: Optional[str] = None) -> Dict[str, Any]:
    """
    List all saved papers, optionally filtered by topic.

    Args:
        topic: Optional topic filter (will search in topic directory names)

    Returns:
        Dictionary containing saved papers information
    """
    try:
        if not os.path.exists(PAPER_DIR):
            return {"error": "No papers directory found. Search for papers first.", "papers": []}

        all_papers = []
        topics_found = []

        for item in os.listdir(PAPER_DIR):
            item_path = os.path.join(PAPER_DIR, item)
            if os.path.isdir(item_path):
                # If topic filter is specified, check if it matches
                if topic and topic.lower().replace(" ", "_") not in item.lower():
                    continue
                
                topics_found.append(item)
                file_path = os.path.join(item_path, "papers_info.json")
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r", encoding='utf-8') as json_file:
                            papers_info = json.load(json_file)
                            for paper_id, paper_data in papers_info.items():
                                paper_summary = {
                                    "id": paper_id,
                                    "title": paper_data.get("title", "Unknown"),
                                    "authors": paper_data.get("authors", []),
                                    "published": paper_data.get("published", "Unknown"),
                                    "topic_category": item,
                                    "categories": paper_data.get("categories", [])
                                }
                                all_papers.append(paper_summary)
                    except (FileNotFoundError, json.JSONDecodeError) as e:
                        logger.warning(f"Error reading {file_path}: {str(e)}")
                        continue

        result = {
            "total_papers": len(all_papers),
            "topics_found": topics_found,
            "topic_filter": topic,
            "papers": all_papers,
            "timestamp": datetime.now().isoformat()
        }

        logger.info("Listed saved papers", total=len(all_papers), topics=len(topics_found))
        return result

    except Exception as e:
        logger.error("List saved papers failed", error=str(e))
        return {"error": f"Error listing papers: {str(e)}", "papers": []}


def download_paper(paper_id: str, session_id: str = "", download_dir: Optional[str] = None) -> str:
    """
    Download a paper PDF by its ID (session-aware).

    Args:
        paper_id: The ArXiv paper ID
        session_id: Session ID (if provided, download to session directory)
        download_dir: Optional directory to save the PDF (defaults to papers/downloads or session papers dir)

    Returns:
        Status message about the download
    """
    try:
        # Determine download directory
        if session_id and download_dir is None:
            # Session manager will be handled by server layer
            download_dir = os.path.join(PAPER_DIR, "downloads")

        if download_dir is None:
            download_dir = os.path.join(PAPER_DIR, "downloads")

        os.makedirs(download_dir, exist_ok=True)

        # Search for paper in ArXiv
        client = arxiv.Client()
        search = arxiv.Search(id_list=[paper_id])

        papers = list(client.results(search))
        if not papers:
            return f"Paper {paper_id} not found on ArXiv"

        paper = papers[0]

        # Download PDF
        filename = f"{paper_id.replace('/', '_')}.pdf"
        file_path = os.path.join(download_dir, filename)

        paper.download_pdf(dirpath=download_dir, filename=filename)

        logger.info("Paper downloaded", paper_id=paper_id, file_path=file_path, session_id=session_id)
        return f"Successfully downloaded {paper.title} to {file_path}"

    except Exception as e:
        logger.error("Paper download failed", paper_id=paper_id, error=str(e))
        return f"Error downloading paper {paper_id}: {str(e)}"


def search_papers_by_author(author_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search for papers by a specific author on ArXiv.

    Args:
        author_name: Name of the author to search for
        max_results: Maximum number of results to retrieve (default: 10)

    Returns:
        List of paper information dictionaries
    """
    try:
        # 确保 max_results 是有效的正整数
        max_results = max(1, int(max_results))
        logger.info(f"Starting author search with max_results={max_results}", author=author_name)

        client = arxiv.Client()

        # Search for papers by author
        search = arxiv.Search(
            query=f"au:{author_name}",
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )

        # 获取结果并限制数量
        paper_list = []
        for i, paper in enumerate(client.results(search)):
            if i >= max_results:
                break
            paper_info = {
                'id': paper.get_short_id(),
                'title': paper.title,
                'authors': [author.name for author in paper.authors],
                'summary': paper.summary[:500] + "..." if len(paper.summary) > 500 else paper.summary,
                'pdf_url': paper.pdf_url,
                'published': str(paper.published.date()),
                'categories': paper.categories
            }
            paper_list.append(paper_info)

        logger.info(
            "Author search completed",
            author=author_name,
            requested_max_results=max_results,
            actual_results=len(paper_list)
        )
        return paper_list

    except Exception as e:
        logger.error("Author search failed", author=author_name, error=str(e))
        return [{"error": f"Search failed: {str(e)}"}]


async def get_arxiv_paper_content_async(arxiv_id: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    异步获取ArXiv论文PDF的全文内容（带重试机制）。

    Args:
        arxiv_id: ArXiv论文ID（例如 "2301.07041"）
        timeout: 超时时间（秒）

    Returns:
        包含论文ID、提取的文本和元数据的字典
    """
    pdf_url = f'http://arxiv.org/pdf/{arxiv_id}.pdf'

    for attempt in range(MAX_RETRIES + 1):
        try:
            logger.debug(f'Fetching ArXiv paper content for {arxiv_id} (attempt {attempt+1}/{MAX_RETRIES+1})')

            # 使用 aiohttp 异步下载PDF
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 403:
                        logger.warning(f"Access forbidden (403) for ArXiv paper: {arxiv_id}")
                        break  # 不重试 403 错误

                    resp.raise_for_status()

                    content = await resp.read()
                    reader = PdfReader(BytesIO(content))
                    text = '\n'.join(page.extract_text() or '' for page in reader.pages)

                    metadata = {
                        'arxiv_id': arxiv_id,
                        'source': 'arxiv',
                        'pdf_url': pdf_url,
                        'abs_url': f'http://arxiv.org/abs/{arxiv_id}',
                        'document_type': 'research_paper',
                        'text_length': len(text),
                        'page_count': len(reader.pages),
                        'extraction_timestamp': datetime.now().isoformat()
                    }

                    logger.info(f'Extracted {len(text)} characters from ArXiv paper {arxiv_id}')

                    return {
                        'id': arxiv_id,
                        'content': text,
                        'metadata': metadata,
                        'status': 'success'
                    }

        except asyncio.TimeoutError:
            logger.warning(f'Timeout fetching ArXiv paper {arxiv_id} (attempt {attempt+1}/{MAX_RETRIES+1})')
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.warning(f'Error fetching ArXiv paper {arxiv_id} (attempt {attempt+1}/{MAX_RETRIES+1}): {str(e)}')
            if attempt < MAX_RETRIES and "403" not in str(e):
                await asyncio.sleep(RETRY_DELAY)
                continue
            break

    logger.error(f'Failed to fetch ArXiv paper {arxiv_id} after {MAX_RETRIES+1} attempts')
    return {
        'id': arxiv_id,
        'content': '',
        'metadata': {},
        'status': 'error',
        'error': 'Failed to fetch paper after retries'
    }


def get_arxiv_paper_content(arxiv_id: str) -> Dict[str, Any]:
    """
    获取ArXiv论文PDF的全文内容（同步版本，保持向后兼容）。

    Args:
        arxiv_id: ArXiv论文ID（例如 "2301.07041"）

    Returns:
        包含论文ID、提取的文本和元数据的字典
    """
    pdf_url = f'http://arxiv.org/pdf/{arxiv_id}.pdf'

    for attempt in range(MAX_RETRIES + 1):
        try:
            logger.debug(f'Fetching ArXiv paper content for {arxiv_id} (attempt {attempt+1}/{MAX_RETRIES+1})')

            resp = requests.get(pdf_url, timeout=DEFAULT_TIMEOUT)

            if resp.status_code == 403:
                logger.warning(f"Access forbidden (403) for ArXiv paper: {arxiv_id}")
                break  # 不重试 403 错误

            resp.raise_for_status()

            reader = PdfReader(BytesIO(resp.content))
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)

            metadata = {
                'arxiv_id': arxiv_id,
                'source': 'arxiv',
                'pdf_url': pdf_url,
                'abs_url': f'http://arxiv.org/abs/{arxiv_id}',
                'document_type': 'research_paper',
                'text_length': len(text),
                'page_count': len(reader.pages),
                'extraction_timestamp': datetime.now().isoformat()
            }

            logger.info(f'Extracted {len(text)} characters from ArXiv paper {arxiv_id}')

            return {
                'id': arxiv_id,
                'content': text,
                'metadata': metadata,
                'status': 'success'
            }

        except requests.Timeout:
            logger.warning(f'Timeout fetching ArXiv paper {arxiv_id} (attempt {attempt+1}/{MAX_RETRIES+1})')
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.warning(f'Error fetching ArXiv paper {arxiv_id} (attempt {attempt+1}/{MAX_RETRIES+1}): {str(e)}')
            if attempt < MAX_RETRIES and "403" not in str(e):
                time.sleep(RETRY_DELAY)
                continue
            break

    logger.error(f'Failed to fetch ArXiv paper {arxiv_id} after {MAX_RETRIES+1} attempts')
    return {
        'id': arxiv_id,
        'content': '',
        'metadata': {},
        'status': 'error',
        'error': 'Failed to fetch paper after retries'
    }

