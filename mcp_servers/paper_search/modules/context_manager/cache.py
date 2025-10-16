"""
Context Manager Module (上下文管理模块)

解决问题：
1. 重复检索 - 避免在同一会话中重复搜索相同的查询
2. 上下文丢失 - 保持搜索历史和结果缓存

功能：
1. 搜索历史管理
2. 结果缓存
3. 会话状态跟踪
4. 智能去重
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)

# 缓存目录
CACHE_DIR = "mcp_servers/paper_search/cache"
SEARCH_HISTORY_FILE = os.path.join(CACHE_DIR, "search_history.json")
RESULTS_CACHE_DIR = os.path.join(CACHE_DIR, "results")

# 缓存过期时间（小时）
CACHE_EXPIRY_HOURS = 24


class SearchContextManager:
    """搜索上下文管理器"""
    
    def __init__(self):
        self.search_history = {}
        self.results_cache = {}
        self.current_session = None
        self._ensure_cache_dirs()
        self._load_search_history()
    
    def _ensure_cache_dirs(self):
        """确保缓存目录存在"""
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(RESULTS_CACHE_DIR, exist_ok=True)
    
    def _load_search_history(self):
        """加载搜索历史"""
        try:
            if os.path.exists(SEARCH_HISTORY_FILE):
                with open(SEARCH_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.search_history = json.load(f)
                logger.info(f"Loaded search history with {len(self.search_history)} entries")
            else:
                self.search_history = {}
        except Exception as e:
            logger.error(f"Failed to load search history: {e}")
            self.search_history = {}
    
    def _save_search_history(self):
        """保存搜索历史"""
        try:
            with open(SEARCH_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.search_history, f, indent=2, ensure_ascii=False)
            logger.debug("Search history saved")
        except Exception as e:
            logger.error(f"Failed to save search history: {e}")
    
    def _generate_query_hash(self, query: str, source: str, **kwargs) -> str:
        """生成查询的唯一哈希值"""
        # 创建查询的唯一标识
        query_data = {
            'query': query.lower().strip(),
            'source': source,
            **kwargs
        }
        query_str = json.dumps(query_data, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: str) -> bool:
        """检查缓存是否有效"""
        try:
            cache_time = datetime.fromisoformat(timestamp)
            expiry_time = cache_time + timedelta(hours=CACHE_EXPIRY_HOURS)
            return datetime.now() < expiry_time
        except Exception:
            return False
    
    def check_recent_search(
        self, 
        query: str, 
        source: str, 
        **kwargs
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        检查是否有最近的相同搜索
        
        Args:
            query: 搜索查询
            source: 搜索源 (arxiv, tavily, google_scholar)
            **kwargs: 其他搜索参数
            
        Returns:
            如果找到有效缓存，返回 (cache_file_path, cached_results)
            否则返回 None
        """
        query_hash = self._generate_query_hash(query, source, **kwargs)
        
        # 检查搜索历史
        if query_hash in self.search_history:
            history_entry = self.search_history[query_hash]
            
            # 检查缓存是否有效
            if self._is_cache_valid(history_entry['timestamp']):
                cache_file = history_entry.get('cache_file')
                if cache_file and os.path.exists(cache_file):
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cached_results = json.load(f)
                        
                        logger.info(f"Found valid cache for query: {query[:50]}...")
                        logger.info(f"Cache file: {cache_file}")
                        logger.info(f"Cached {len(cached_results.get('results', []))} results")
                        
                        return cache_file, cached_results
                    except Exception as e:
                        logger.error(f"Failed to load cache file {cache_file}: {e}")
        
        return None
    
    def save_search_results(
        self, 
        query: str, 
        source: str, 
        results: List[Dict[str, Any]], 
        **kwargs
    ) -> str:
        """
        保存搜索结果到缓存
        
        Args:
            query: 搜索查询
            source: 搜索源
            results: 搜索结果
            **kwargs: 其他搜索参数
            
        Returns:
            缓存文件路径
        """
        try:
            query_hash = self._generate_query_hash(query, source, **kwargs)
            timestamp = datetime.now().isoformat()
            
            # 创建缓存文件
            cache_filename = f"{source}_{query_hash}_{timestamp.replace(':', '-')}.json"
            cache_file = os.path.join(RESULTS_CACHE_DIR, cache_filename)
            
            # 保存结果
            cache_data = {
                'query': query,
                'source': source,
                'timestamp': timestamp,
                'parameters': kwargs,
                'total_results': len(results),
                'results': results
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            # 更新搜索历史
            self.search_history[query_hash] = {
                'query': query,
                'source': source,
                'timestamp': timestamp,
                'cache_file': cache_file,
                'total_results': len(results)
            }
            
            self._save_search_history()
            
            logger.info(f"Saved {len(results)} results to cache: {cache_file}")
            return cache_file
            
        except Exception as e:
            logger.error(f"Failed to save search results: {e}")
            return ""
    
    def get_session_searches(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的搜索历史"""
        session_searches = []
        for query_hash, entry in self.search_history.items():
            if entry.get('session_id') == session_id:
                session_searches.append(entry)
        
        # 按时间排序
        session_searches.sort(key=lambda x: x['timestamp'], reverse=True)
        return session_searches
    
    def cleanup_expired_cache(self):
        """清理过期的缓存文件"""
        try:
            cleaned_count = 0
            for query_hash, entry in list(self.search_history.items()):
                if not self._is_cache_valid(entry['timestamp']):
                    # 删除缓存文件
                    cache_file = entry.get('cache_file')
                    if cache_file and os.path.exists(cache_file):
                        os.remove(cache_file)
                    
                    # 从历史中删除
                    del self.search_history[query_hash]
                    cleaned_count += 1
            
            if cleaned_count > 0:
                self._save_search_history()
                logger.info(f"Cleaned up {cleaned_count} expired cache entries")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        valid_entries = 0
        expired_entries = 0
        total_results = 0
        
        for entry in self.search_history.values():
            if self._is_cache_valid(entry['timestamp']):
                valid_entries += 1
                total_results += entry.get('total_results', 0)
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self.search_history),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'total_cached_results': total_results,
            'cache_dir': CACHE_DIR,
            'expiry_hours': CACHE_EXPIRY_HOURS
        }


# 全局上下文管理器实例
_context_manager = None

def get_context_manager() -> SearchContextManager:
    """获取全局上下文管理器实例"""
    global _context_manager
    if _context_manager is None:
        _context_manager = SearchContextManager()
    return _context_manager


def check_and_use_cache(query: str, source: str, **kwargs) -> Optional[List[Dict[str, Any]]]:
    """
    检查并使用缓存（便捷函数）
    
    Returns:
        如果找到有效缓存，返回结果列表；否则返回 None
    """
    context_manager = get_context_manager()
    cache_result = context_manager.check_recent_search(query, source, **kwargs)
    
    if cache_result:
        cache_file, cached_data = cache_result
        return cached_data.get('results', [])
    
    return None


def save_to_cache(query: str, source: str, results: List[Dict[str, Any]], **kwargs) -> str:
    """
    保存到缓存（便捷函数）
    
    Returns:
        缓存文件路径
    """
    context_manager = get_context_manager()
    return context_manager.save_search_results(query, source, results, **kwargs)
