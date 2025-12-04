"""
URL 转换工具模块 - 将本地文件路径转换为 API URL

功能：
1. 文件路径 → 下载 URL
2. 图片路径 → 图片 URL
3. 确保所有对外返回的路径都是 /api/... 格式

注意：
- 所有 URL 都是相对路径（/api/...）
- 前端或 Nginx 会自动补全域名
"""

from pathlib import Path
from typing import Union
import structlog

logger = structlog.get_logger(__name__)


def file_to_download_url(file_path: Union[str, Path], session_id: str) -> str:
    """
    将本地文件路径转换为下载 URL
    
    Args:
        file_path: 本地文件路径
        session_id: 会话 ID
    
    Returns:
        下载 URL（格式：/api/download/papers/{session_id}/{filename}）
    
    Examples:
        >>> file_to_download_url("/path/to/session_data/papers/session_123/report.md", "session_123")
        '/api/download/papers/session_123/report.md'
    """
    path = Path(file_path)
    filename = path.name
    
    # 生成标准的下载 URL
    url = f"/api/download/papers/{session_id}/{filename}"
    
    logger.debug(f"Converted file path to download URL: {file_path} -> {url}")
    return url


def file_to_image_url(file_path: Union[str, Path], session_id: str, subpath: str = "") -> str:
    """
    将图片路径转换为图片 URL
    
    Args:
        file_path: 本地文件路径
        session_id: 会话 ID
        subpath: 子路径（如 phonon_results/structure_1）
    
    Returns:
        图片 URL（格式：/api/images/phonon/{session_id}/{subpath}/{filename}）
    
    Examples:
        >>> file_to_image_url("/path/to/phonon.png", "session_123", "phonon_results")
        '/api/images/phonon/session_123/phonon_results/phonon.png'
    """
    path = Path(file_path)
    filename = path.name
    
    # 构建 URL
    if subpath:
        url = f"/api/images/phonon/{session_id}/{subpath}/{filename}"
    else:
        url = f"/api/images/phonon/{session_id}/{filename}"
    
    logger.debug(f"Converted file path to image URL: {file_path} -> {url}")
    return url


def extract_session_id_from_path(file_path: Union[str, Path]) -> str:
    """
    从文件路径中提取会话 ID
    
    Args:
        file_path: 文件路径
    
    Returns:
        会话 ID（如果找不到则返回空字符串）
    
    Examples:
        >>> extract_session_id_from_path("/data/session_data/papers/session_123/file.csv")
        'session_123'
    """
    path_str = str(file_path).replace('\\', '/')
    
    # 尝试匹配 session_xxx 格式
    import re
    match = re.search(r'session_[0-9]+_[a-z0-9]+', path_str)
    if match:
        return match.group(0)
    
    return ""


def normalize_api_url(url: str) -> str:
    """
    规范化 API URL，确保以 /api/ 开头
    
    Args:
        url: 原始 URL
    
    Returns:
        规范化后的 URL
    
    Examples:
        >>> normalize_api_url("download/papers/session_123/file.csv")
        '/api/download/papers/session_123/file.csv'
        >>> normalize_api_url("/api/download/papers/session_123/file.csv")
        '/api/download/papers/session_123/file.csv'
    """
    url = url.strip()
    
    # 如果已经以 /api/ 开头，直接返回
    if url.startswith('/api/'):
        return url
    
    # 如果以 / 开头但不是 /api/，添加 api
    if url.startswith('/'):
        if not url.startswith('/api'):
            return '/api' + url
        return url
    
    # 否则添加 /api/ 前缀
    return '/api/' + url

