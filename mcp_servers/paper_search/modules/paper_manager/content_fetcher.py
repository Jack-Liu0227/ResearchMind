"""
Content Fetcher Module (内容获取模块)

功能：
1. 通用URL全文提取
2. PDF文本提取
3. HTML文本提取
4. 失败时回退到摘要
"""
import requests
from typing import Dict, Any
from datetime import datetime
import structlog
from io import BytesIO

logger = structlog.get_logger(__name__)

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


def fetch_content_from_url(
    url: str,
    paper_id: str = None,
    fallback_abstract: str = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Fetch full text content from a URL (PDF or HTML).
    
    Args:
        url: URL to fetch content from
        paper_id: Paper ID for logging
        fallback_abstract: Abstract to use if content fetching fails
        timeout: Request timeout in seconds
    
    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - content: Extracted text content
        - metadata: Metadata about the extraction
        - error: Error message (if status is 'error')
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
        
        # Determine content type
        if url.endswith('.pdf') or 'pdf' in url.lower():
            return _fetch_pdf_content(url, paper_id, fallback_abstract, timeout)
        else:
            return _fetch_html_content(url, paper_id, fallback_abstract, timeout)
    
    except Exception as e:
        logger.error(f"Failed to fetch content from {url}: {e}", paper_id=paper_id)
        
        # Fallback to abstract
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


def _fetch_pdf_content(
    url: str,
    paper_id: str,
    fallback_abstract: str,
    timeout: int
) -> Dict[str, Any]:
    """Fetch content from PDF URL."""
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
    
    try:
        # Download PDF
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # Extract text from PDF
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
    
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}", paper_id=paper_id)
        
        # Fallback to abstract
        if fallback_abstract:
            return {
                'status': 'success',
                'content': fallback_abstract,
                'metadata': {
                    'fallback': True,
                    'fallback_reason': f'PDF extraction failed: {str(e)}',
                    'extraction_timestamp': datetime.now().isoformat()
                }
            }
        
        return {
            'status': 'error',
            'content': '',
            'error': str(e),
            'metadata': {}
        }


def _fetch_html_content(
    url: str,
    paper_id: str,
    fallback_abstract: str,
    timeout: int
) -> Dict[str, Any]:
    """Fetch content from HTML URL."""
    try:
        # Download HTML
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # Extract text from HTML
        if BS4_AVAILABLE:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
        else:
            # Fallback: use raw text
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
    
    except Exception as e:
        logger.error(f"HTML extraction failed: {e}", paper_id=paper_id)
        
        # Fallback to abstract
        if fallback_abstract:
            return {
                'status': 'success',
                'content': fallback_abstract,
                'metadata': {
                    'fallback': True,
                    'fallback_reason': f'HTML extraction failed: {str(e)}',
                    'extraction_timestamp': datetime.now().isoformat()
                }
            }
        
        return {
            'status': 'error',
            'content': '',
            'error': str(e),
            'metadata': {}
        }


def get_paper_content_by_source(
    paper: Dict[str, Any],
    source: str = None
) -> Dict[str, Any]:
    """
    Get paper content based on source type.
    
    Args:
        paper: Paper dict with url, pdf_url, abstract, etc.
        source: Source type (arxiv, tavily, etc.)
    
    Returns:
        Dict with status, content, and metadata
    """
    # Auto-detect source
    if not source:
        source = paper.get('source', 'unknown')
    
    # For ArXiv, use specialized function
    if source == 'arxiv':
        from ..search.arxiv import get_arxiv_paper_content
        arxiv_id = paper.get('id') or paper.get('paper_id')
        if arxiv_id:
            return get_arxiv_paper_content(arxiv_id)
    
    # For other sources, try URL extraction
    url = paper.get('pdf_url') or paper.get('url')
    abstract = paper.get('abstract') or paper.get('summary', '')
    paper_id = paper.get('paper_id', 'unknown')
    
    return fetch_content_from_url(
        url=url,
        paper_id=paper_id,
        fallback_abstract=abstract
    )

