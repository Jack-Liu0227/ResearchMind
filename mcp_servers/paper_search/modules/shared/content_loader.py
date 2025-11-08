"""
内容加载工具 - 用于按需加载已保存的大型内容

功能：
1. 从文件路径加载完整内容
2. 分段加载大型文件
3. 提供内容搜索功能
"""

import os
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


def load_paper_content(file_path: str) -> Dict[str, Any]:
    """
    从文件加载论文内容
    
    Args:
        file_path: 文件路径
    
    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - content: 文件内容
        - file_path: 文件路径
        - size: 文件大小（字节）
    """
    try:
        if not os.path.exists(file_path):
            return {
                'status': 'error',
                'error': f'File not found: {file_path}',
                'file_path': file_path
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_size = os.path.getsize(file_path)
        
        logger.info(f"Loaded content from file: {file_path} ({file_size} bytes)")
        
        return {
            'status': 'success',
            'content': content,
            'file_path': file_path,
            'size': file_size,
            'length': len(content)
        }
    
    except Exception as e:
        logger.error(f"Failed to load content from file: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'file_path': file_path
        }


def load_paper_content_segment(
    file_path: str,
    start: int = 0,
    length: int = 5000
) -> Dict[str, Any]:
    """
    分段加载论文内容
    
    Args:
        file_path: 文件路径
        start: 起始位置（字符数）
        length: 读取长度（字符数）
    
    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - content: 内容片段
        - start: 起始位置
        - length: 实际读取长度
        - total_size: 文件总大小
        - has_more: 是否还有更多内容
    """
    try:
        if not os.path.exists(file_path):
            return {
                'status': 'error',
                'error': f'File not found: {file_path}'
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            f.seek(start)
            content = f.read(length)
        
        file_size = os.path.getsize(file_path)
        actual_length = len(content)
        has_more = (start + actual_length) < file_size
        
        logger.info(f"Loaded segment from {file_path}: {start}-{start+actual_length}")
        
        return {
            'status': 'success',
            'content': content,
            'start': start,
            'length': actual_length,
            'total_size': file_size,
            'has_more': has_more,
            'file_path': file_path
        }
    
    except Exception as e:
        logger.error(f"Failed to load content segment: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'file_path': file_path
        }


def search_in_content_file(
    file_path: str,
    search_term: str,
    context_length: int = 200
) -> Dict[str, Any]:
    """
    在内容文件中搜索关键词
    
    Args:
        file_path: 文件路径
        search_term: 搜索词
        context_length: 上下文长度（每个匹配项前后的字符数）
    
    Returns:
        Dict containing:
        - status: 'success' or 'error'
        - matches: 匹配结果列表
        - total_matches: 匹配总数
    """
    try:
        if not os.path.exists(file_path):
            return {
                'status': 'error',
                'error': f'File not found: {file_path}'
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找所有匹配
        matches = []
        search_lower = search_term.lower()
        content_lower = content.lower()
        
        pos = 0
        while True:
            pos = content_lower.find(search_lower, pos)
            if pos == -1:
                break
            
            # 提取上下文
            start = max(0, pos - context_length)
            end = min(len(content), pos + len(search_term) + context_length)
            context = content[start:end]
            
            matches.append({
                'position': pos,
                'context': context,
                'match': content[pos:pos+len(search_term)]
            })
            
            pos += 1
        
        logger.info(f"Found {len(matches)} matches for '{search_term}' in {file_path}")
        
        return {
            'status': 'success',
            'matches': matches,
            'total_matches': len(matches),
            'search_term': search_term,
            'file_path': file_path
        }
    
    except Exception as e:
        logger.error(f"Failed to search in content file: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'file_path': file_path
        }

