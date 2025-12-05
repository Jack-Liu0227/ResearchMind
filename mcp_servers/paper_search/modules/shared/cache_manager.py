"""
缓存管理模块

功能：
1. 分析结果缓存 - 避免重复分析相同论文
2. 缓存键生成 - 基于 paper_id + abstract 的哈希
3. 缓存过期管理 - 支持 TTL
4. 缓存统计 - 命中率、大小等
"""
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)


class CacheManager:
    """分析结果缓存管理器"""

    def __init__(self, cache_dir: str = None, ttl: int = 0):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径（如果为 None，使用配置中的 CACHE_DIR）
            ttl: 缓存过期时间（秒），0 表示永不过期
        """
        # 🔧 使用统一的配置路径
        if cache_dir is None:
            # 添加 paper_search 目录到 sys.path
            import sys
            from pathlib import Path as PathLib
            _CURRENT_FILE = PathLib(__file__)
            _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
            if str(_PAPER_SEARCH_DIR) not in sys.path:
                sys.path.insert(0, str(_PAPER_SEARCH_DIR))

            from config import CACHE_DIR
            cache_dir = str(CACHE_DIR)

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'writes': 0,
            'errors': 0
        }
        
        logger.info(f"CacheManager initialized", cache_dir=str(self.cache_dir), ttl=ttl)
    
    def _get_cache_key(self, paper: Dict[str, Any]) -> str:
        """
        生成论文的缓存键
        
        使用 paper_id + abstract 的 MD5 哈希作为缓存键
        这样即使论文 ID 相同，但摘要不同，也会被视为不同的论文
        
        Args:
            paper: 论文信息字典
            
        Returns:
            缓存键（MD5 哈希）
        """
        paper_id = paper.get('paper_id', '')
        abstract = paper.get('abstract', '')
        
        # 组合 paper_id 和 abstract
        content = f"{paper_id}:{abstract}"
        
        # 生成 MD5 哈希
        cache_key = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        return cache_key
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_expired(self, cache_file: Path) -> bool:
        """检查缓存是否过期"""
        if self.ttl == 0:
            return False  # 永不过期
        
        if not cache_file.exists():
            return True
        
        # 检查文件修改时间
        file_mtime = cache_file.stat().st_mtime
        current_time = time.time()
        
        return (current_time - file_mtime) > self.ttl
    
    def get(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取分析结果
        
        Args:
            paper: 论文信息字典
            
        Returns:
            缓存的分析结果，如果不存在或过期则返回 None
        """
        try:
            cache_key = self._get_cache_key(paper)
            cache_file = self._get_cache_file(cache_key)
            
            # 检查缓存是否存在且未过期
            if not cache_file.exists():
                self.stats['misses'] += 1
                logger.debug(f"Cache miss: {paper.get('paper_id', 'unknown')}")
                return None
            
            if self._is_expired(cache_file):
                self.stats['misses'] += 1
                logger.debug(f"Cache expired: {paper.get('paper_id', 'unknown')}")
                # 删除过期缓存
                cache_file.unlink()
                return None
            
            # 读取缓存
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_result = json.load(f)
            
            self.stats['hits'] += 1
            logger.info(f"✅ Cache hit: {paper.get('paper_id', 'unknown')}")
            
            return cached_result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"Failed to read cache: {e}")
            return None
    
    def set(self, paper: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        将分析结果保存到缓存
        
        Args:
            paper: 论文信息字典
            result: 分析结果
            
        Returns:
            是否保存成功
        """
        try:
            cache_key = self._get_cache_key(paper)
            cache_file = self._get_cache_file(cache_key)
            
            # 添加缓存元数据
            cached_data = {
                **result,
                '_cache_metadata': {
                    'cached_at': time.time(),
                    'cache_key': cache_key,
                    'paper_id': paper.get('paper_id', 'unknown')
                }
            }
            
            # 保存到文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, ensure_ascii=False, indent=2)
            
            self.stats['writes'] += 1
            logger.info(f"💾 Cached analysis: {paper.get('paper_id', 'unknown')}")
            
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"Failed to write cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'cache_size': self._get_cache_size()
        }
    
    def _get_cache_size(self) -> int:
        """获取缓存文件数量"""
        return len(list(self.cache_dir.glob('*.json')))
    
    def clear(self) -> int:
        """
        清空所有缓存
        
        Returns:
            删除的文件数量
        """
        count = 0
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Failed to delete cache file {cache_file}: {e}")
        
        logger.info(f"Cleared {count} cache files")
        return count
    
    def clear_expired(self) -> int:
        """
        清除过期的缓存
        
        Returns:
            删除的文件数量
        """
        if self.ttl == 0:
            return 0  # 永不过期，无需清理
        
        count = 0
        for cache_file in self.cache_dir.glob('*.json'):
            if self._is_expired(cache_file):
                try:
                    cache_file.unlink()
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete expired cache {cache_file}: {e}")
        
        logger.info(f"Cleared {count} expired cache files")
        return count


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager

    if _cache_manager is None:
        # 添加 paper_search 目录到 sys.path
        import sys
        from pathlib import Path as PathLib
        _CURRENT_FILE = PathLib(__file__)
        _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
        if str(_PAPER_SEARCH_DIR) not in sys.path:
            sys.path.insert(0, str(_PAPER_SEARCH_DIR))

        from config import CACHE_DIR, CACHE_EXPIRY
        _cache_manager = CacheManager(cache_dir=CACHE_DIR, ttl=CACHE_EXPIRY)

    return _cache_manager

