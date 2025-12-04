"""
统一路径管理模块 - 消除硬编码路径，使用环境变量配置

功能：
1. 提供统一的路径获取接口
2. 支持环境变量配置
3. 自动创建必要的目录
4. 跨平台兼容（使用 pathlib.Path）

环境变量：
- SESSION_DATA_ROOT: 会话数据根目录（默认：data/session_data）
- PAPERS_ROOT: 论文存储目录（默认：data/papers）
- PHONON_ROOT: 声子数据目录（默认：data/phonon）
"""

import os
from pathlib import Path
from typing import Union, List
import structlog

logger = structlog.get_logger(__name__)

# 项目根目录（ResearchMind 根目录）
_PROJECT_ROOT = Path(__file__).parent.parent


def session_data_root() -> Path:
    """
    获取会话数据根目录

    环境变量：SESSION_DATA_ROOT
    默认值：data/session_data

    Returns:
        会话数据根目录的 Path 对象
    """
    env_path = os.getenv('SESSION_DATA_ROOT')
    if env_path:
        # 如果是相对路径，相对于项目根目录
        path = Path(env_path)
        if not path.is_absolute():
            path = _PROJECT_ROOT / path
    else:
        # 默认路径
        path = _PROJECT_ROOT / "data" / "session_data"

    return path.resolve()


def papers_root() -> Path:
    """
    获取论文存储目录
    
    环境变量：PAPERS_ROOT
    默认值：data/papers（实际上是 session_data/papers）
    
    Returns:
        论文存储目录的 Path 对象
    """
    env_path = os.getenv('PAPERS_ROOT')
    if env_path:
        path = Path(env_path)
        if not path.is_absolute():
            path = _PROJECT_ROOT / path
    else:
        # 默认使用 session_data/papers
        path = session_data_root() / "papers"
    
    return path.resolve()


def phonon_root() -> Path:
    """
    获取声子数据目录
    
    环境变量：PHONON_ROOT
    默认值：data/phonon（实际上是 session_data/simulation）
    
    Returns:
        声子数据目录的 Path 对象
    """
    env_path = os.getenv('PHONON_ROOT')
    if env_path:
        path = Path(env_path)
        if not path.is_absolute():
            path = _PROJECT_ROOT / path
    else:
        # 默认使用 session_data/simulation
        path = session_data_root() / "simulation"
    
    return path.resolve()


def ensure_dirs(*paths: Union[str, Path]) -> None:
    """
    确保指定的所有目录存在，不存在则创建
    
    Args:
        *paths: 一个或多个目录路径（str 或 Path 对象）
    
    Examples:
        ensure_dirs(session_data_root(), papers_root())
        ensure_dirs("/path/to/dir1", "/path/to/dir2")
    """
    for path in paths:
        path_obj = Path(path)
        if not path_obj.exists():
            path_obj.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path_obj}")
        elif not path_obj.is_dir():
            logger.warning(f"Path exists but is not a directory: {path_obj}")


def get_session_path(session_id: str, data_type: str = "papers") -> Path:
    """
    获取特定会话的数据路径
    
    Args:
        session_id: 会话 ID
        data_type: 数据类型（papers, structures, phonon_results, etc.）
    
    Returns:
        会话数据路径的 Path 对象
    """
    base = session_data_root()
    
    if data_type == "papers":
        return base / "papers" / session_id
    elif data_type == "structures":
        return base / "structures" / session_id
    elif data_type == "phonon_results":
        return base / "simulation" / session_id / "phonon_results"
    elif data_type == "thermal_conductivity":
        return base / "simulation" / session_id / "thermal_conductivity"
    elif data_type == "cif":
        return base / "simulation" / session_id / "cif"
    elif data_type == "uploads":
        return base / "simulation" / session_id / "cif"
    elif data_type == "relaxed_structures":
        return base / "simulation" / session_id / "relaxed"
    elif data_type == "generated_structures":
        return base / "simulation" / session_id / "generated"
    else:
        # 通用路径
        return base / data_type / session_id

