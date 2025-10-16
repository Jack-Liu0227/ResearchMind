"""
Search Agent Tools (搜索代理工具)

包含所有搜索相关的工具：
- ArXiv 搜索
- Tavily 搜索
"""
from .arxiv import (
    search_arxiv_papers,
    search_papers_by_author,
    get_paper_info,
    list_saved_papers,
    download_paper,
    get_arxiv_paper_content,
)

from .tavily import (
    search_web,
    search_academic_web,
    search_news,
    is_tavily_available,
)

__all__ = [
    # ArXiv
    'search_arxiv_papers',
    'search_papers_by_author',
    'get_paper_info',
    'list_saved_papers',
    'download_paper',
    'get_arxiv_paper_content',

    # Tavily
    'search_web',
    'search_academic_web',
    'search_news',
    'is_tavily_available',
]

