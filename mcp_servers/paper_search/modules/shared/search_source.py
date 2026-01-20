"""
Search Source Module (搜索源模块)

统一搜索接口 - 高优先级优化功能

功能：
1. 定义统一的搜索源抽象基类
2. 标准化搜索结果格式
3. 提供搜索源工厂类

设计模式：策略模式
"""
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# 标准化搜索结果格式
# ============================================================================

class PaperResult:
    """标准化的论文搜索结果"""
    
    def __init__(
        self,
        paper_id: str,
        title: str,
        authors: List[str],
        abstract: str,
        url: str,
        published: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化论文结果
        
        Args:
            paper_id: 论文ID
            title: 标题
            authors: 作者列表
            abstract: 摘要
            url: 论文链接
            published: 发表时间
            source: 来源（arxiv/tavily/google_scholar/cnki）
            metadata: 源特定的额外信息
        """
        self.paper_id = paper_id
        self.title = title
        self.authors = authors
        self.abstract = abstract
        self.url = url
        self.published = published
        self.source = source
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'paper_id': self.paper_id,
            'id': self.paper_id,  # 兼容旧格式
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'summary': self.abstract,  # 兼容旧格式
            'url': self.url,
            'pdf_url': self.url,  # 兼容旧格式
            'published': self.published,
            'source': self.source,
            'metadata': self.metadata,
            'timestamp': datetime.now().isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaperResult':
        """从字典创建实例"""
        return cls(
            paper_id=data.get('paper_id') or data.get('id', 'unknown'),
            title=data.get('title', ''),
            authors=data.get('authors', []),
            abstract=data.get('abstract') or data.get('summary', ''),
            url=data.get('url') or data.get('pdf_url', ''),
            published=data.get('published', ''),
            source=data.get('source', 'unknown'),
            metadata=data.get('metadata', {})
        )


# ============================================================================
# 搜索源抽象基类
# ============================================================================

class SearchSource(ABC):
    """搜索源抽象基类"""
    
    def __init__(self, source_name: str):
        """
        初始化搜索源
        
        Args:
            source_name: 搜索源名称
        """
        self.source_name = source_name
        logger.info(f"Initialized search source: {source_name}")
    
    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[PaperResult]:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            **kwargs: 源特定的额外参数
        
        Returns:
            标准化的论文结果列表
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        检查搜索源是否可用
        
        Returns:
            True if available, False otherwise
        """
        pass
    
    def get_source_name(self) -> str:
        """获取搜索源名称"""
        return self.source_name


# ============================================================================
# 具体搜索源实现
# ============================================================================

class ArxivSearchSource(SearchSource):
    """ArXiv 搜索源"""
    
    def __init__(self):
        super().__init__("arxiv")
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[PaperResult]:
        """执行 ArXiv 搜索"""
        from .arxiv import search_arxiv_papers, get_paper_info
        import json
        
        try:
            # 调用现有的 ArXiv 搜索函数
            paper_ids = search_arxiv_papers(query, max_results)
            
            results = []
            for paper_id in paper_ids:
                try:
                    # 获取论文信息
                    paper_info_str = get_paper_info(paper_id)
                    paper_info = json.loads(paper_info_str)
                    
                    # 转换为标准格式
                    result = PaperResult(
                        paper_id=paper_id,
                        title=paper_info.get('title', ''),
                        authors=paper_info.get('authors', []),
                        abstract=paper_info.get('summary', ''),
                        url=paper_info.get('pdf_url', ''),
                        published=paper_info.get('published', ''),
                        source='arxiv',
                        metadata={
                            'categories': paper_info.get('categories', []),
                            'primary_category': paper_info.get('primary_category', '')
                        }
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to get info for paper {paper_id}: {e}")
            
            return results
        except Exception as e:
            logger.error(f"ArXiv search failed: {e}")
            return []
    
    def is_available(self) -> bool:
        """ArXiv 总是可用"""
        return True


class TavilySearchSource(SearchSource):
    """Tavily 搜索源"""
    
    def __init__(self):
        super().__init__("tavily")
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[PaperResult]:
        """执行 Tavily 搜索"""
        from .tavily import search_academic_web
        
        try:
            # 调用现有的 Tavily 搜索函数
            tavily_results = await search_academic_web(query, max_results)
            
            results = []
            for item in tavily_results:
                # 转换为标准格式
                result = PaperResult(
                    paper_id=item.get('url', ''),  # Tavily 没有 paper_id，使用 URL
                    title=item.get('title', ''),
                    authors=[],  # Tavily 不提供作者信息
                    abstract=item.get('content', ''),
                    url=item.get('url', ''),
                    published=item.get('published_date', ''),
                    source='tavily',
                    metadata={
                        'score': item.get('score', 0),
                        'raw_content': item.get('raw_content', '')
                    }
                )
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []
    
    def is_available(self) -> bool:
        """检查 Tavily 是否可用"""
        from .tavily import is_tavily_available
        return is_tavily_available()


class SemanticScholarSearchSource(SearchSource):
    """Semantic Scholar 搜索源"""

    def __init__(self):
        super().__init__("semantic_scholar")

    async def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[PaperResult]:
        """执行 Semantic Scholar 搜索"""
        from .semantic_scholar import search_semantic_scholar_papers

        try:
            semantic_results = await search_semantic_scholar_papers(query, max_results)
            results = []
            for item in semantic_results:
                result = PaperResult(
                    paper_id=item.get('paper_id') or item.get('id', '') or item.get('title', ''),
                    title=item.get('title', ''),
                    authors=item.get('authors', []),
                    abstract=item.get('abstract', ''),
                    url=item.get('url', ''),
                    published=item.get('published', ''),
                    source='semantic_scholar',
                    metadata={
                        'doi': item.get('doi', ''),
                        'journal_name': item.get('journal_name', ''),
                        'categories': item.get('categories', []),
                        'citation_count': item.get('citation_count', 0),
                        'external_ids': item.get('external_ids', {}),
                        'pdf_url': item.get('pdf_url', ''),
                    }
                )
                results.append(result)
            return results
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []

    def is_available(self) -> bool:
        """Semantic Scholar 允许无 key 访问"""
        return True


# ============================================================================
# 搜索源工厂
# ============================================================================

class SearchSourceFactory:
    """搜索源工厂类"""
    
    _sources = {
        'arxiv': ArxivSearchSource,
        'tavily': TavilySearchSource,
        'semantic_scholar': SemanticScholarSearchSource,
    }
    
    @classmethod
    def create(cls, source_name: str) -> Optional[SearchSource]:
        """
        创建搜索源实例
        
        Args:
            source_name: 搜索源名称
        
        Returns:
            搜索源实例，如果不存在则返回 None
        """
        source_class = cls._sources.get(source_name.lower())
        if source_class:
            return source_class()
        else:
            logger.error(f"Unknown search source: {source_name}")
            return None
    
    @classmethod
    def get_available_sources(cls) -> List[str]:
        """
        获取所有可用的搜索源
        
        Returns:
            可用搜索源名称列表
        """
        available = []
        for name, source_class in cls._sources.items():
            try:
                source = source_class()
                if source.is_available():
                    available.append(name)
            except Exception as e:
                logger.error(f"Failed to check availability of {name}: {e}")
        
        return available

