"""
Field Mapping and Normalization for Multi-Source Papers

统一字段标准：
- paper_id: 主键，ArXiv使用arxiv_id，其他源使用DOI或URL hash
- title: 标题
- authors: 作者列表
- abstract: 摘要
- url: 访问链接
- pdf_url: PDF下载链接（如果有）
- published: 发表时间
- source: 来源（arxiv, tavily, scholar, etc.）
- doi: DOI（如果有）
- categories: 分类/标签
"""
from typing import Dict, Any, List
import hashlib


def normalize_paper_fields(paper: Dict[str, Any], source: str = None) -> Dict[str, Any]:
    """
    Normalize paper fields from different sources to a unified format.
    
    Args:
        paper: Raw paper data from any source
        source: Source type (arxiv, tavily, scholar, etc.)
    
    Returns:
        Normalized paper dict with standard fields
    """
    # Auto-detect source if not provided
    if not source:
        source = paper.get('source', 'unknown')
    
    # Extract paper_id based on source
    paper_id = _extract_paper_id(paper, source)
    
    # Normalize fields
    normalized = {
        'paper_id': paper_id,
        'title': _extract_title(paper),
        'authors': _extract_authors(paper),
        'abstract': _extract_abstract(paper),
        'url': _extract_url(paper),
        'pdf_url': _extract_pdf_url(paper),
        'published': _extract_published(paper),
        'source': source,
        'doi': _extract_doi(paper),
        'categories': _extract_categories(paper),
    }

    # Add optional fields if present
    optional_fields = [
        'score',
        'published_date',
        'citation_count',
        'publication_types',
        'external_ids',
        'id',  # 保留原始 ID
        'summary',  # 保留摘要的别名
        'journal_name',
        'journal_name',
    ]

    for field in optional_fields:
        if field in paper and paper[field] is not None:
            normalized[field] = paper[field]

    return normalized


def _extract_paper_id(paper: Dict[str, Any], source: str) -> str:
    """Extract or generate paper_id based on source."""
    # Try common ID fields
    for field in ['paper_id', 'id', 'arxiv_id']:
        if field in paper and paper[field]:
            return str(paper[field])
    
    # Try DOI
    doi = _extract_doi(paper)
    if doi:
        return f"doi_{doi.replace('/', '_')}"
    
    # Fallback: use URL hash
    url = _extract_url(paper)
    if url:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"{source}_{url_hash}"
    
    # Last resort: use title hash
    title = _extract_title(paper)
    if title:
        title_hash = hashlib.md5(title.encode()).hexdigest()[:12]
        return f"{source}_{title_hash}"
    
    return f"{source}_unknown"


def _extract_title(paper: Dict[str, Any]) -> str:
    """Extract title from paper."""
    return paper.get('title', '') or ''


def _extract_authors(paper: Dict[str, Any]) -> List[str]:
    """Extract authors from paper."""
    authors = paper.get('authors', [])
    
    # Handle different formats
    if isinstance(authors, list):
        return [str(a) for a in authors]
    elif isinstance(authors, str):
        # Split by comma if it's a string
        return [a.strip() for a in authors.split(',')]
    
    return []


def _extract_abstract(paper: Dict[str, Any]) -> str:
    """Extract abstract from paper."""
    # Try different field names
    for field in ['abstract', 'summary', 'content']:
        if field in paper and paper[field]:
            return str(paper[field])
    return ''


def _extract_url(paper: Dict[str, Any]) -> str:
    """Extract URL from paper."""
    # Try different field names
    for field in ['url', 'link', 'entry_id', 'abs_url']:
        if field in paper and paper[field]:
            return str(paper[field])
    return ''


def _extract_pdf_url(paper: Dict[str, Any]) -> str:
    """Extract PDF URL from paper."""
    # Try different field names
    for field in ['pdf_url', 'download_url']:
        if field in paper and paper[field]:
            return str(paper[field])
    
    # For ArXiv, construct PDF URL from ID
    if 'arxiv_id' in paper or 'id' in paper:
        arxiv_id = paper.get('arxiv_id') or paper.get('id')
        if arxiv_id and 'arxiv' in paper.get('source', '').lower():
            return f"http://arxiv.org/pdf/{arxiv_id}.pdf"
    
    return ''


def _extract_published(paper: Dict[str, Any]) -> str:
    """Extract publication date from paper."""
    # Try different field names
    for field in ['published', 'published_date', 'date', 'year']:
        if field in paper and paper[field]:
            return str(paper[field])
    return ''


def _extract_doi(paper: Dict[str, Any]) -> str:
    """Extract DOI from paper."""
    doi = paper.get('doi', '')
    if doi:
        return str(doi)
    
    # Try to extract from URL
    url = _extract_url(paper)
    if 'doi.org/' in url:
        return url.split('doi.org/')[-1]
    
    return ''


def _extract_categories(paper: Dict[str, Any]) -> List[str]:
    """Extract categories from paper."""
    categories = paper.get('categories', [])
    
    # Handle different formats
    if isinstance(categories, list):
        return [str(c) for c in categories]
    elif isinstance(categories, str):
        # Split by comma if it's a string
        return [c.strip() for c in categories.split(',')]
    
    return []


def batch_normalize_papers(papers: List[Dict[str, Any]], source: str = None) -> List[Dict[str, Any]]:
    """
    Normalize a batch of papers.
    
    Args:
        papers: List of raw paper dicts
        source: Source type (if all papers are from same source)
    
    Returns:
        List of normalized paper dicts
    """
    return [normalize_paper_fields(paper, source) for paper in papers]


def merge_paper_data(papers_list: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Merge papers from multiple sources, removing duplicates.
    
    Args:
        papers_list: List of paper lists from different sources
    
    Returns:
        Merged and deduplicated list of papers
    """
    merged_by_id: Dict[str, Dict[str, Any]] = {}

    def _merge_fields(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        if not existing:
            return incoming

        # Prefer richer text fields if missing
        for key in ["title", "abstract", "summary", "url", "pdf_url", "published", "doi", "journal_name"]:
            if not existing.get(key) and incoming.get(key):
                existing[key] = incoming[key]

        # Prefer longer author list if existing is empty
        if not existing.get("authors") and incoming.get("authors"):
            existing["authors"] = incoming["authors"]
        elif incoming.get("authors") and len(incoming.get("authors", [])) > len(existing.get("authors", [])):
            existing["authors"] = incoming["authors"]

        # Categories: use incoming if existing empty
        if not existing.get("categories") and incoming.get("categories"):
            existing["categories"] = incoming["categories"]

        # Citation count: keep the max if available
        try:
            existing_cc = int(existing.get("citation_count") or 0)
        except (TypeError, ValueError):
            existing_cc = 0
        try:
            incoming_cc = int(incoming.get("citation_count") or 0)
        except (TypeError, ValueError):
            incoming_cc = 0
        if incoming_cc > existing_cc:
            existing["citation_count"] = incoming_cc

        # Preserve other optional fields if missing
        for key in ["score", "published_date", "publication_types", "external_ids", "id"]:
            if key in incoming and (existing.get(key) in (None, "", [])):
                existing[key] = incoming[key]

        return existing

    for papers in papers_list:
        for paper in papers:
            normalized = normalize_paper_fields(paper)
            paper_id = normalized['paper_id']

            if paper_id in merged_by_id:
                merged_by_id[paper_id] = _merge_fields(merged_by_id[paper_id], normalized)
            else:
                merged_by_id[paper_id] = normalized

    return list(merged_by_id.values())

