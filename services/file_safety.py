"""
文件操作安全工具

提供文件操作的错误处理、磁盘空间检查、临时文件清理等功能
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Union
from functools import wraps

logger = logging.getLogger(__name__)


def check_disk_space(path: Union[str, Path], required_mb: int = 100) -> bool:
    """
    检查磁盘空间是否足够
    
    Args:
        path: 要检查的路径
        required_mb: 需要的最小空间（MB）
    
    Returns:
        是否有足够空间
    """
    try:
        stat = shutil.disk_usage(path)
        available_mb = stat.free / (1024 * 1024)
        
        if available_mb < required_mb:
            logger.warning(
                f"⚠️ 磁盘空间不足: 可用 {available_mb:.2f} MB，需要 {required_mb} MB"
            )
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ 检查磁盘空间失败: {e}")
        return False


def safe_write_file(
    file_path: Union[str, Path],
    content: Union[str, bytes],
    encoding: str = 'utf-8',
    check_space: bool = True
) -> bool:
    """
    安全地写入文件
    
    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 编码（仅用于文本模式）
        check_space: 是否检查磁盘空间
    
    Returns:
        是否成功
    """
    try:
        file_path = Path(file_path)
        
        # 检查磁盘空间
        if check_space:
            content_size_mb = len(content) / (1024 * 1024)
            required_mb = max(content_size_mb * 2, 100)  # 预留2倍空间或至少100MB
            
            if not check_disk_space(file_path.parent, required_mb):
                logger.error(f"❌ 磁盘空间不足，无法写入文件: {file_path}")
                return False
        
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        if isinstance(content, bytes):
            with open(file_path, 'wb') as f:
                f.write(content)
        else:
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
        
        logger.debug(f"✅ 文件写入成功: {file_path}")
        return True
        
    except PermissionError as e:
        logger.error(f"❌ 文件写入权限不足: {file_path} - {e}")
        return False
    except OSError as e:
        logger.error(f"❌ 文件写入失败（磁盘错误）: {file_path} - {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 文件写入失败: {file_path} - {e}", exc_info=True)
        return False


def safe_read_file(
    file_path: Union[str, Path],
    encoding: str = 'utf-8',
    binary: bool = False,
    max_size_mb: int = 100
) -> Optional[Union[str, bytes]]:
    """
    安全地读取文件
    
    Args:
        file_path: 文件路径
        encoding: 编码（仅用于文本模式）
        binary: 是否以二进制模式读取
        max_size_mb: 最大文件大小（MB）
    
    Returns:
        文件内容，失败返回 None
    """
    try:
        file_path = Path(file_path)
        
        # 检查文件是否存在
        if not file_path.exists():
            logger.error(f"❌ 文件不存在: {file_path}")
            return None
        
        # 检查文件大小
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            logger.error(
                f"❌ 文件过大: {file_path} ({file_size_mb:.2f} MB > {max_size_mb} MB)"
            )
            return None
        
        # 读取文件
        if binary:
            with open(file_path, 'rb') as f:
                return f.read()
        else:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        
    except PermissionError as e:
        logger.error(f"❌ 文件读取权限不足: {file_path} - {e}")
        return None
    except UnicodeDecodeError as e:
        logger.error(f"❌ 文件编码错误: {file_path} - {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 文件读取失败: {file_path} - {e}", exc_info=True)
        return None


def safe_delete_file(file_path: Union[str, Path]) -> bool:
    """
    安全地删除文件

    Args:
        file_path: 文件路径

    Returns:
        是否成功
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            logger.debug(f"文件不存在，无需删除: {file_path}")
            return True

        file_path.unlink()
        logger.debug(f"✅ 文件删除成功: {file_path}")
        return True

    except PermissionError as e:
        logger.error(f"❌ 文件删除权限不足: {file_path} - {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 文件删除失败: {file_path} - {e}", exc_info=True)
        return False


def safe_delete_directory(dir_path: Union[str, Path], ignore_errors: bool = True) -> bool:
    """
    安全地删除目录

    Args:
        dir_path: 目录路径
        ignore_errors: 是否忽略错误

    Returns:
        是否成功
    """
    try:
        dir_path = Path(dir_path)

        if not dir_path.exists():
            logger.debug(f"目录不存在，无需删除: {dir_path}")
            return True

        shutil.rmtree(dir_path, ignore_errors=ignore_errors)
        logger.debug(f"✅ 目录删除成功: {dir_path}")
        return True

    except PermissionError as e:
        logger.error(f"❌ 目录删除权限不足: {dir_path} - {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 目录删除失败: {dir_path} - {e}", exc_info=True)
        return False


def with_file_error_handling(fallback_value=None):
    """
    文件操作错误处理装饰器

    Args:
        fallback_value: 发生错误时的返回值

    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except PermissionError as e:
                logger.error(f"❌ 权限错误: {func.__name__} - {e}")
                return fallback_value
            except OSError as e:
                logger.error(f"❌ 系统错误: {func.__name__} - {e}")
                return fallback_value
            except Exception as e:
                logger.error(f"❌ 未知错误: {func.__name__} - {e}", exc_info=True)
                return fallback_value
        return wrapper
    return decorator


async def with_async_file_error_handling(fallback_value=None):
    """
    异步文件操作错误处理装饰器

    Args:
        fallback_value: 发生错误时的返回值

    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except PermissionError as e:
                logger.error(f"❌ 权限错误: {func.__name__} - {e}")
                return fallback_value
            except OSError as e:
                logger.error(f"❌ 系统错误: {func.__name__} - {e}")
                return fallback_value
            except Exception as e:
                logger.error(f"❌ 未知错误: {func.__name__} - {e}", exc_info=True)
                return fallback_value
        return wrapper
    return decorator


