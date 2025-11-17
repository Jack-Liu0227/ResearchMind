"""
Paper Manager Agent Tools (论文管理代理工具)

包含所有论文管理相关的工具：
- 论文下载
- 论文分析
- 向量化存储
- 导出工具
"""
from ..search.arxiv import (
    download_paper,
    get_arxiv_paper_content,
)

from .content_fetcher import (
    fetch_content_from_url_async,
    get_paper_content_by_source_async,
)

from .analysis import (
    analyze_paper_content,
    batch_paper_analysis,
)

from .export_tools import (
    save_papers_to_csv,
    save_summary_to_file,
    save_report_to_file,
    read_papers_from_csv,
)

# 向量化工具从 data_layer 导入
try:
    import sys
    from pathlib import Path
    # Add parent directory to path
    parent_dir = Path(__file__).parent.parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from data_layer import ingest_papers_to_vector_store
except ImportError:
    # Fallback: define a placeholder
    def ingest_papers_to_vector_store(*args, **kwargs):
        raise NotImplementedError("data_layer not available")

__all__ = [
    # 下载
    'download_paper',
    'get_arxiv_paper_content',

    # 内容获取（异步）
    'fetch_content_from_url_async',
    'get_paper_content_by_source_async',

    # 分析
    'analyze_paper_content',
    'batch_paper_analysis',

    # 向量化
    'ingest_papers_to_vector_store',

    # 导出
    'save_papers_to_csv',
    'save_summary_to_file',
    'save_report_to_file',
    'read_papers_from_csv',
]

