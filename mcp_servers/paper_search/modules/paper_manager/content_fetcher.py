"""
Content Fetcher Module (内容获取模块)

功能：
1. 通用URL全文提取（支持异步）
2. PDF文本提取
3. HTML文本提取
4. 失败时回退到摘要
5. 超时控制和重试机制
"""
import asyncio
import aiohttp
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from io import BytesIO
import time

logger = structlog.get_logger(__name__)

# 全局超时配置
DEFAULT_TIMEOUT = 30  # 默认超时时间（秒）
MAX_RETRIES = 2  # 最大重试次数
RETRY_DELAY = 1  # 重试延迟（秒）
MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 最大内容大小（10MB）

# Try to import PDF reader
try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyPDF2 not available, PDF extraction will be disabled")

# Try to import HTML parser
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("BeautifulSoup not available, HTML extraction will be limited")


async def fetch_content_from_url_async(
    url: str,
    paper_id: str = None,
    fallback_abstract: str = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """
    异步获取URL内容（PDF或HTML）。

    Args:
        url: 要获取的URL
        paper_id: 论文ID（用于日志）
        fallback_abstract: 获取失败时的备用摘要
        timeout: 请求超时时间（秒）

    Returns:
        包含以下内容的字典：
        - status: 'success' 或 'error'
        - content: 提取的文本内容
        - metadata: 提取的元数据
        - error: 错误信息（如果status为'error'）
    """
    if not url:
        return {
            'status': 'error',
            'content': fallback_abstract or '',
            'error': 'No URL provided',
            'metadata': {'fallback': True}
        }

    try:
        logger.info(f"Fetching content from URL (async): {url}", paper_id=paper_id)

        # 确定内容类型
        if url.endswith('.pdf') or 'pdf' in url.lower():
            return await _fetch_pdf_content_async(url, paper_id, fallback_abstract, timeout)
        else:
            return await _fetch_html_content_async(url, paper_id, fallback_abstract, timeout)

    except Exception as e:
        logger.error(f"Failed to fetch content from {url}: {e}", paper_id=paper_id)

        # 回退到摘要
        if fallback_abstract:
            return {
                'status': 'success',
                'content': fallback_abstract,
                'metadata': {
                    'fallback': True,
                    'fallback_reason': str(e),
                    'extraction_timestamp': datetime.now().isoformat()
                }
            }

        return {
            'status': 'error',
            'content': '',
            'error': str(e),
            'metadata': {}
        }


def fetch_content_from_url(
    url: str,
    paper_id: str = None,
    fallback_abstract: str = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """
    同步获取URL内容（保持向后兼容）。

    Args:
        url: 要获取的URL
        paper_id: 论文ID（用于日志）
        fallback_abstract: 获取失败时的备用摘要
        timeout: 请求超时时间（秒）

    Returns:
        包含以下内容的字典：
        - status: 'success' 或 'error'
        - content: 提取的文本内容
        - metadata: 提取的元数据
        - error: 错误信息（如果status为'error'）
    """
    if not url:
        return {
            'status': 'error',
            'content': fallback_abstract or '',
            'error': 'No URL provided',
            'metadata': {'fallback': True}
        }

    try:
        logger.info(f"Fetching content from URL: {url}", paper_id=paper_id)

        # 确定内容类型
        if url.endswith('.pdf') or 'pdf' in url.lower():
            return _fetch_pdf_content(url, paper_id, fallback_abstract, timeout)
        else:
            return _fetch_html_content(url, paper_id, fallback_abstract, timeout)

    except Exception as e:
        logger.error(f"Failed to fetch content from {url}: {e}", paper_id=paper_id)

        # 回退到摘要
        if fallback_abstract:
            return {
                'status': 'success',
                'content': fallback_abstract,
                'metadata': {
                    'fallback': True,
                    'fallback_reason': str(e),
                    'extraction_timestamp': datetime.now().isoformat()
                }
            }

        return {
            'status': 'error',
            'content': '',
            'error': str(e),
            'metadata': {}
        }


async def _fetch_pdf_content_async(
    url: str,
    paper_id: str,
    fallback_abstract: str,
    timeout: int
) -> Dict[str, Any]:
    """异步获取PDF内容（带重试机制）。"""
    if not PDF_AVAILABLE:
        logger.warning("PyPDF2 not available, falling back to abstract")
        return {
            'status': 'success',
            'content': fallback_abstract or '',
            'metadata': {
                'fallback': True,
                'fallback_reason': 'PyPDF2 not available'
            }
        }

    for attempt in range(MAX_RETRIES + 1):
        try:
            # 使用 aiohttp 异步下载 PDF
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    if response.status == 403:
                        logger.warning(f"Access forbidden (403) for PDF: {url}", paper_id=paper_id)
                        break  # 不重试 403 错误

                    response.raise_for_status()

                    # 检查内容大小
                    content = await response.read()
                    if len(content) > MAX_CONTENT_SIZE:
                        logger.warning(f"PDF too large ({len(content)} bytes), using abstract", paper_id=paper_id)
                        raise ValueError(f"PDF too large: {len(content)} bytes")

                    # 提取PDF文本
                    reader = PdfReader(BytesIO(content))
                    text = '\n'.join(page.extract_text() or '' for page in reader.pages)

                    if not text or len(text) < 100:
                        raise ValueError("Extracted text is too short or empty")

                    metadata = {
                        'url': url,
                        'source_type': 'pdf',
                        'text_length': len(text),
                        'page_count': len(reader.pages),
                        'extraction_timestamp': datetime.now().isoformat(),
                        'fallback': False
                    }

                    logger.info(f"Successfully extracted {len(text)} characters from PDF", paper_id=paper_id)

                    return {
                        'status': 'success',
                        'content': text,
                        'metadata': metadata
                    }

        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching PDF (attempt {attempt+1}/{MAX_RETRIES+1}): {url}", paper_id=paper_id)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.warning(f"PDF extraction failed (attempt {attempt+1}/{MAX_RETRIES+1}): {e}", paper_id=paper_id)
            if attempt < MAX_RETRIES and "403" not in str(e):
                await asyncio.sleep(RETRY_DELAY)
                continue
            break

    # 回退到摘要
    if fallback_abstract:
        return {
            'status': 'success',
            'content': fallback_abstract,
            'metadata': {
                'fallback': True,
                'fallback_reason': 'PDF extraction failed after retries',
                'extraction_timestamp': datetime.now().isoformat()
            }
        }

    return {
        'status': 'error',
        'content': '',
        'error': 'PDF extraction failed',
        'metadata': {}
    }


def _fetch_pdf_content(
    url: str,
    paper_id: str,
    fallback_abstract: str,
    timeout: int
) -> Dict[str, Any]:
    """同步获取PDF内容（保持向后兼容）。"""
    if not PDF_AVAILABLE:
        logger.warning("PyPDF2 not available, falling back to abstract")
        return {
            'status': 'success',
            'content': fallback_abstract or '',
            'metadata': {
                'fallback': True,
                'fallback_reason': 'PyPDF2 not available'
            }
        }

    for attempt in range(MAX_RETRIES + 1):
        try:
            # 下载PDF（带超时控制）
            response = requests.get(url, timeout=timeout)

            if response.status_code == 403:
                logger.warning(f"Access forbidden (403) for PDF: {url}", paper_id=paper_id)
                break  # 不重试 403 错误

            response.raise_for_status()

            # 检查内容大小
            if len(response.content) > MAX_CONTENT_SIZE:
                logger.warning(f"PDF too large ({len(response.content)} bytes), using abstract", paper_id=paper_id)
                raise ValueError(f"PDF too large: {len(response.content)} bytes")

            # 提取PDF文本
            reader = PdfReader(BytesIO(response.content))
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)

            if not text or len(text) < 100:
                raise ValueError("Extracted text is too short or empty")

            metadata = {
                'url': url,
                'source_type': 'pdf',
                'text_length': len(text),
                'page_count': len(reader.pages),
                'extraction_timestamp': datetime.now().isoformat(),
                'fallback': False
            }

            logger.info(f"Successfully extracted {len(text)} characters from PDF", paper_id=paper_id)

            return {
                'status': 'success',
                'content': text,
                'metadata': metadata
            }

        except requests.Timeout:
            logger.warning(f"Timeout fetching PDF (attempt {attempt+1}/{MAX_RETRIES+1}): {url}", paper_id=paper_id)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.warning(f"PDF extraction failed (attempt {attempt+1}/{MAX_RETRIES+1}): {e}", paper_id=paper_id)
            if attempt < MAX_RETRIES and "403" not in str(e):
                time.sleep(RETRY_DELAY)
                continue
            break

    # 回退到摘要
    if fallback_abstract:
        return {
            'status': 'success',
            'content': fallback_abstract,
            'metadata': {
                'fallback': True,
                'fallback_reason': 'PDF extraction failed after retries',
                'extraction_timestamp': datetime.now().isoformat()
            }
        }

    return {
        'status': 'error',
        'content': '',
        'error': 'PDF extraction failed',
        'metadata': {}
    }


async def _fetch_html_content_async(
    url: str,
    paper_id: str,
    fallback_abstract: str,
    timeout: int
) -> Dict[str, Any]:
    """异步获取HTML内容（带重试机制）。"""
    for attempt in range(MAX_RETRIES + 1):
        try:
            # 使用 aiohttp 异步下载 HTML
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    if response.status == 403:
                        logger.warning(f"Access forbidden (403) for HTML: {url}", paper_id=paper_id)
                        break  # 不重试 403 错误

                    response.raise_for_status()

                    # 检查内容大小
                    content = await response.read()
                    if len(content) > MAX_CONTENT_SIZE:
                        logger.warning(f"HTML too large ({len(content)} bytes), using abstract", paper_id=paper_id)
                        raise ValueError(f"HTML too large: {len(content)} bytes")

                    # 提取HTML文本
                    if BS4_AVAILABLE:
                        soup = BeautifulSoup(content, 'html.parser')

                        # 移除脚本和样式元素
                        for script in soup(["script", "style"]):
                            script.decompose()

                        # 获取文本
                        text = soup.get_text()

                        # 清理空白
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                    else:
                        # 回退：使用原始文本
                        text = content.decode('utf-8', errors='ignore')

                    if not text or len(text) < 100:
                        raise ValueError("Extracted text is too short or empty")

                    metadata = {
                        'url': url,
                        'source_type': 'html',
                        'text_length': len(text),
                        'extraction_timestamp': datetime.now().isoformat(),
                        'fallback': False
                    }

                    logger.info(f"Successfully extracted {len(text)} characters from HTML", paper_id=paper_id)

                    return {
                        'status': 'success',
                        'content': text,
                        'metadata': metadata
                    }

        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching HTML (attempt {attempt+1}/{MAX_RETRIES+1}): {url}", paper_id=paper_id)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.warning(f"HTML extraction failed (attempt {attempt+1}/{MAX_RETRIES+1}): {e}", paper_id=paper_id)
            if attempt < MAX_RETRIES and "403" not in str(e):
                await asyncio.sleep(RETRY_DELAY)
                continue
            break

    # 回退到摘要
    if fallback_abstract:
        return {
            'status': 'success',
            'content': fallback_abstract,
            'metadata': {
                'fallback': True,
                'fallback_reason': 'HTML extraction failed after retries',
                'extraction_timestamp': datetime.now().isoformat()
            }
        }

    return {
        'status': 'error',
        'content': '',
        'error': 'HTML extraction failed',
        'metadata': {}
    }


def _fetch_html_content(
    url: str,
    paper_id: str,
    fallback_abstract: str,
    timeout: int
) -> Dict[str, Any]:
    """同步获取HTML内容（保持向后兼容）。"""
    for attempt in range(MAX_RETRIES + 1):
        try:
            # 下载HTML（带超时控制）
            response = requests.get(url, timeout=timeout)

            if response.status_code == 403:
                logger.warning(f"Access forbidden (403) for HTML: {url}", paper_id=paper_id)
                break  # 不重试 403 错误

            response.raise_for_status()

            # 检查内容大小
            if len(response.content) > MAX_CONTENT_SIZE:
                logger.warning(f"HTML too large ({len(response.content)} bytes), using abstract", paper_id=paper_id)
                raise ValueError(f"HTML too large: {len(response.content)} bytes")

            # 提取HTML文本
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.content, 'html.parser')

                # 移除脚本和样式元素
                for script in soup(["script", "style"]):
                    script.decompose()

                # 获取文本
                text = soup.get_text()

                # 清理空白
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
            else:
                # 回退：使用原始文本
                text = response.text

            if not text or len(text) < 100:
                raise ValueError("Extracted text is too short or empty")

            metadata = {
                'url': url,
                'source_type': 'html',
                'text_length': len(text),
                'extraction_timestamp': datetime.now().isoformat(),
                'fallback': False
            }

            logger.info(f"Successfully extracted {len(text)} characters from HTML", paper_id=paper_id)

            return {
                'status': 'success',
                'content': text,
                'metadata': metadata
            }

        except requests.Timeout:
            logger.warning(f"Timeout fetching HTML (attempt {attempt+1}/{MAX_RETRIES+1}): {url}", paper_id=paper_id)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.warning(f"HTML extraction failed (attempt {attempt+1}/{MAX_RETRIES+1}): {e}", paper_id=paper_id)
            if attempt < MAX_RETRIES and "403" not in str(e):
                time.sleep(RETRY_DELAY)
                continue
            break

    # 回退到摘要
    if fallback_abstract:
        return {
            'status': 'success',
            'content': fallback_abstract,
            'metadata': {
                'fallback': True,
                'fallback_reason': 'HTML extraction failed after retries',
                'extraction_timestamp': datetime.now().isoformat()
            }
        }

    return {
        'status': 'error',
        'content': '',
        'error': 'HTML extraction failed',
        'metadata': {}
    }


async def get_paper_content_by_source_async(
    paper: Dict[str, Any],
    source: str = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """
    异步获取论文内容（基于来源类型）。

    Args:
        paper: 论文字典（包含url、pdf_url、abstract等）
        source: 来源类型（arxiv、tavily等）
        timeout: 超时时间（秒）

    Returns:
        包含status、content和metadata的字典
    """
    # 自动检测来源
    if not source:
        source = paper.get('source', 'unknown')

    # 对于ArXiv，使用专门的函数
    if source == 'arxiv':
        from ..search.arxiv import get_arxiv_paper_content_async
        arxiv_id = paper.get('id') or paper.get('paper_id')
        if arxiv_id:
            return await get_arxiv_paper_content_async(arxiv_id, timeout=timeout)

    # 对于其他来源，尝试URL提取
    url = paper.get('pdf_url') or paper.get('url')
    abstract = paper.get('abstract') or paper.get('summary', '')
    paper_id = paper.get('paper_id', 'unknown')

    return await fetch_content_from_url_async(
        url=url,
        paper_id=paper_id,
        fallback_abstract=abstract,
        timeout=timeout
    )


def get_paper_content_by_source(
    paper: Dict[str, Any],
    source: str = None
) -> Dict[str, Any]:
    """
    获取论文内容（基于来源类型）。

    Args:
        paper: 论文字典（包含url、pdf_url、abstract等）
        source: 来源类型（arxiv、tavily等）

    Returns:
        包含status、content和metadata的字典
    """
    # 自动检测来源
    if not source:
        source = paper.get('source', 'unknown')

    # 对于ArXiv，使用专门的函数
    if source == 'arxiv':
        from ..search.arxiv import get_arxiv_paper_content
        arxiv_id = paper.get('id') or paper.get('paper_id')
        if arxiv_id:
            return get_arxiv_paper_content(arxiv_id)

    # 对于其他来源，尝试URL提取
    url = paper.get('pdf_url') or paper.get('url')
    abstract = paper.get('abstract') or paper.get('summary', '')
    paper_id = paper.get('paper_id', 'unknown')

    return fetch_content_from_url(
        url=url,
        paper_id=paper_id,
        fallback_abstract=abstract
    )

