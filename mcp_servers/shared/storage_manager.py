"""
统一存储管理器 - 管理所有 MCP 服务器的文件存储

功能：
1. 提供统一的 session_data 目录结构
2. 管理不同类型数据的存储路径
3. 支持会话隔离和数据迁移
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# 项目根目录
_MODULE_DIR = Path(__file__).parent.parent.parent  # ResearchMind根目录
SESSION_DATA_DIR = _MODULE_DIR / "session_data"

# 确保根目录存在
SESSION_DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_session_storage_path(
    session_id: str,
    data_type: str,
    create: bool = True
) -> Path:
    """
    获取会话存储路径
    
    Args:
        session_id: 会话ID
        data_type: 数据类型 (papers, structures, phonon_results, thermal_conductivity, cif, etc.)
        create: 是否创建目录
    
    Returns:
        存储路径
    """
    # 根据数据类型确定子目录
    if data_type == "papers":
        base_path = SESSION_DATA_DIR / "papers" / session_id
    elif data_type == "structures":
        base_path = SESSION_DATA_DIR / "structures" / session_id
    elif data_type == "phonon_results":
        base_path = SESSION_DATA_DIR / "simulation" / session_id / "phonon_results"
    elif data_type == "thermal_conductivity":
        base_path = SESSION_DATA_DIR / "simulation" / session_id / "thermal_conductivity"
    elif data_type == "cif":
        base_path = SESSION_DATA_DIR / "simulation" / session_id / "cif"
    elif data_type == "uploads":
        # CIF 文件上传目录（与 cif 相同）
        base_path = SESSION_DATA_DIR / "simulation" / session_id / "cif"
    elif data_type == "relaxed_structures":
        base_path = SESSION_DATA_DIR / "simulation" / session_id / "relaxed"
    elif data_type == "generated_structures":
        base_path = SESSION_DATA_DIR / "simulation" / session_id / "generated"
    else:
        # 通用路径
        base_path = SESSION_DATA_DIR / data_type / session_id
    
    if create:
        base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created storage path: {base_path}")
    
    return base_path


def get_legacy_path(data_type: str) -> Optional[Path]:
    """
    获取旧的存储路径（用于数据迁移）
    
    Args:
        data_type: 数据类型
    
    Returns:
        旧路径（如果存在）
    """
    legacy_paths = {
        "papers": _MODULE_DIR / "mcp_servers" / "paper_search" / "papers",
        "phonon_results": _MODULE_DIR / "mcp_servers" / "simulation" / "phonon_results",
        "thermal_conductivity": _MODULE_DIR / "mcp_servers" / "simulation" / "thermal_conductivity_results",
        "cif": _MODULE_DIR / "mcp_servers" / "simulation" / "cif",
        "generated_structures": _MODULE_DIR / "mcp_servers" / "simulation" / "crystallm" / "generated_structures",
    }
    
    path = legacy_paths.get(data_type)
    if path and path.exists():
        return path
    return None


def migrate_legacy_data(data_type: str, session_id: str = "legacy") -> bool:
    """
    迁移旧数据到新的存储结构
    
    Args:
        data_type: 数据类型
        session_id: 目标会话ID（默认: legacy）
    
    Returns:
        是否成功迁移
    """
    legacy_path = get_legacy_path(data_type)
    if not legacy_path:
        logger.info(f"No legacy data found for {data_type}")
        return False
    
    new_path = get_session_storage_path(session_id, data_type, create=True)
    
    try:
        import shutil
        
        # 复制文件（保留原文件）
        if legacy_path.is_dir():
            for item in legacy_path.iterdir():
                if item.is_file():
                    target = new_path / item.name
                    if not target.exists():
                        shutil.copy2(item, target)
                        logger.info(f"Migrated: {item.name}")
        
        logger.info(f"Successfully migrated {data_type} from {legacy_path} to {new_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to migrate {data_type}: {e}")
        return False


def get_file_url(file_path: Path, data_type: str, session_id: Optional[str] = None) -> str:
    """
    生成前端可访问的文件 URL

    Args:
        file_path: 文件路径
        data_type: 数据类型
        session_id: 会话 ID（可选，用于生成会话隔离的 URL）

    Returns:
        URL 路径
    """
    # 根据数据类型生成对应的 URL
    filename = file_path.name

    # 如果提供了 session_id，生成会话隔离的 URL
    if session_id:
        if data_type == "phonon_results":
            return f"/api/images/phonon/{session_id}/phonon_results/{filename}"
        elif data_type == "thermal_conductivity":
            return f"/api/files/thermal_conductivity/{session_id}/thermal_conductivity/{filename}"
        elif data_type == "cif" or data_type == "uploads":
            return f"/api/structures/{session_id}/cif/{filename}"
        elif data_type == "relaxed_structures":
            return f"/api/structures/{session_id}/relaxed/{filename}"
        elif data_type == "generated_structures":
            return f"/api/images/generated_structures/{session_id}/generated/{filename}"
        elif data_type == "papers":
            return f"/api/download/papers/{session_id}/{filename}"
        else:
            return f"/api/files/{data_type}/{session_id}/{filename}"

    # 不提供 session_id 时，使用简化的 URL（向后兼容）
    if data_type == "phonon_results":
        return f"/images/phonon/{filename}"
    elif data_type == "thermal_conductivity":
        return f"/files/thermal_conductivity/{filename}"
    elif data_type == "structures" or data_type == "cif":
        return f"/files/structures/{filename}"
    elif data_type == "papers":
        return f"/api/download/{filename}"
    else:
        return f"/files/{data_type}/{filename}"

