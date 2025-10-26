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
import zipfile
from pathlib import Path
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

# Try to import PDF reader (prefer pypdf)
try:
    from pypdf import PdfReader  # type: ignore
    PDF_AVAILABLE = True
except Exception:
    try:
        from PyPDF2 import PdfReader  # type: ignore
        PDF_AVAILABLE = True
    except Exception:
        PDF_AVAILABLE = False
        logger.warning("PyPDF2/pypdf not available, PDF extraction will be disabled")

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
    """
    if not source:
        source = paper.get('source', 'unknown')

    if source == 'arxiv':
        from ..search.arxiv import get_arxiv_paper_content_async
        arxiv_id = paper.get('id') or paper.get('paper_id')
        if arxiv_id:
            return await get_arxiv_paper_content_async(arxiv_id, timeout=timeout)

    if source == 'upload':
        return await _fetch_uploaded_file_async(paper)

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
    """
    if not source:
        source = paper.get('source', 'unknown')

    if source == 'arxiv':
        from ..search.arxiv import get_arxiv_paper_content
        arxiv_id = paper.get('id') or paper.get('paper_id')
        if arxiv_id:
            return get_arxiv_paper_content(arxiv_id)

    if source == 'upload':
        return _fetch_uploaded_file(paper)

    url = paper.get('pdf_url') or paper.get('url')
    abstract = paper.get('abstract') or paper.get('summary', '')
    paper_id = paper.get('paper_id', 'unknown')

    return fetch_content_from_url(
        url=url,
        paper_id=paper_id,
        fallback_abstract=abstract
    )


async def _fetch_uploaded_file_async(paper: Dict[str, Any]) -> Dict[str, Any]:
    return await asyncio.to_thread(_fetch_uploaded_file, paper)


def _fetch_uploaded_file(paper: Dict[str, Any]) -> Dict[str, Any]:
    metadata = paper.get('upload_metadata', {})
    local_path = metadata.get('saved_path') or paper.get('local_file')

    if not local_path:
        return {
            'status': 'error',
            'content': paper.get('abstract', ''),
            'metadata': {
                'fallback': True,
                'fallback_reason': 'No local file recorded for uploaded document'
            }
        }

    path = Path(local_path)
    if not path.is_absolute():
        path = Path('.').resolve() / path
    path = path.resolve()

    if not path.exists():
        logger.warning('Uploaded file not found', expected_path=str(path))
        return {
            'status': 'error',
            'content': paper.get('abstract', ''),
            'metadata': {
                'fallback': True,
                'fallback_reason': f'Uploaded file not found: {path}'
            }
        }

    try:
        text = _extract_uploaded_text(path)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error('Failed to extract uploaded file content', path=str(path), error=str(exc))
        text = ''

    if not text.strip():
        text = paper.get('abstract', '') or '（上传文档已保存，暂未提取文本内容。）'

    return {
        'status': 'success',
        'content': text,
        'metadata': {
            'source_type': 'uploaded_file',
            'local_path': str(path),
            'extraction_timestamp': datetime.now().isoformat()
        }
    }


def _extract_uploaded_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == '.pdf':
        if not PDF_AVAILABLE:
            return '（PDF 内容已保存，本环境未安装 PdfReader 提取文本。）'
        # First attempt via PdfReader
        try:
            reader = PdfReader(path)
            try:
                if getattr(reader, 'is_encrypted', False):
                    reader.decrypt('')
            except Exception:
                pass
            texts = []
            for page in getattr(reader, 'pages', []):
                try:
                    page_text = page.extract_text() or ''
                except Exception:
                    page_text = ''
                if page_text:
                    texts.append(page_text)
            joined = '\n'.join(texts).strip()
            bad_char_ratio = (joined.count('\uFFFD') / max(len(joined), 1)) if joined else 0.0
            if joined and len(joined) >= 50 and bad_char_ratio < 0.05:
                return joined
            # Fallback to pdfminer if result is empty/garbled
            try:
                from pdfminer.high_level import extract_text as pdfminer_extract_text  # type: ignore
                text2 = (pdfminer_extract_text(str(path)) or '').strip()
                return text2 or '（PDF 内容已保存，但未提取到文本。）'
            except Exception as exc2:
                logger.warning('pdfminer.six not available or failed', error=str(exc2))
                return joined or '（PDF 内容已保存，但未提取到文本。）'
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning('Failed to extract PDF text via PdfReader', path=str(path), error=str(exc))
            # Try pdfminer as a last resort
            try:
                from pdfminer.high_level import extract_text as pdfminer_extract_text  # type: ignore
                text3 = (pdfminer_extract_text(str(path)) or '').strip()
                return text3 or '（PDF 内容已保存，但未提取到文本。）'
            except Exception as exc3:
                logger.warning('pdfminer.six not available or failed', error=str(exc3))
                return '（PDF 内容已保存，文本提取失败。）'

    if suffix == '.docx':
        try:
            with zipfile.ZipFile(path) as zf:
                with zf.open('word/document.xml') as doc_xml:
                    xml_content = doc_xml.read().decode('utf-8', errors='ignore')
        except Exception as exc:
            logger.warning('Failed to open DOCX', path=str(path), error=str(exc))
            return '（DOCX 内容已保存，暂未提取文本。）'

        try:
            from xml.etree import ElementTree as ET  # noqa: PLC0415

            tree = ET.fromstring(xml_content)
            namespace = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            paragraphs = [elem.text or '' for elem in tree.iter(f'{namespace}t')]
            text = '\n'.join(paragraphs).strip()
            return text or '（DOCX 内容已保存，但未提取到文本。）'
        except Exception as exc:  # pragma: no cover
            logger.warning('Failed to parse DOCX XML', path=str(path), error=str(exc))
            return '（DOCX 内容已保存，文本提取失败。）'

    if suffix in {'.txt', '.md', '.csv', '.json'}:
        return path.read_text(encoding='utf-8', errors='ignore')

    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return path.read_text(encoding='latin-1', errors='ignore')
