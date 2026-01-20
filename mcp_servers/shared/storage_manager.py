"""
统一存储管理器 - 管理所有 MCP 服务器的文件存储

功能：
1. 提供统一的 session_data 目录结构
2. 管理不同类型数据的存储路径
3. 支持会话隔离和数据迁移
4. 创建和管理会话元数据
"""

import os
import json
import sys
import re
from pathlib import Path
from typing import Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# 🔧 使用统一的路径管理模块
_PROJECT_ROOT = Path(__file__).parent.parent.parent  # ResearchMind根目录
utils_path = _PROJECT_ROOT / "utils"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

from utils.paths import session_data_root, ensure_dirs

# 项目根目录（session_data位于 ../data/session_data）
SESSION_DATA_DIR = session_data_root()

# 确保根目录存在
ensure_dirs(SESSION_DATA_DIR)


def _is_valid_session_id(session_id: Optional[str]) -> bool:
    if not session_id or not isinstance(session_id, str):
        return False
    return re.fullmatch(r"session_\d{13}_[a-z0-9]{8}", session_id) is not None


def get_session_storage_path(
    session_id: str,
    data_type: str,
    create: bool = True,
    session_type: str = "upload",
    created_by: str = "user",
    topic: Optional[str] = None
) -> Path:
    """

    获取会话存储路径

    Args:
        session_id: 会话ID
        data_type: 数据类型 (papers, structures, phonon_results, thermal_conductivity, cif, etc.)
        create: 是否创建目录
        session_type: 会话类型 (upload, search, simulation, etc.)
        created_by: 创建方式 (user, system, api)
        topic: 会话主题（可选）

    Returns:
        存储路径
    """
    if not _is_valid_session_id(session_id):
        raise ValueError(f"Invalid session_id: {session_id}")

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
    elif data_type == "database":
        # 🆕 数据库检索的结构文件 (MP, OQMD, COD, AFLOW)
        base_path = SESSION_DATA_DIR / "simulation" / session_id / "database"
    else:
        # 通用路径
        base_path = SESSION_DATA_DIR / data_type / session_id

    if create:
        # 创建目录
        is_new_session = not base_path.exists()
        base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created storage path: {base_path}")

        # 为 papers 类型创建元数据文件
        if data_type == "papers" and is_new_session:
            _create_session_metadata(
                base_path=base_path,
                session_id=session_id,
                session_type=session_type,
                created_by=created_by,
                topic=topic
            )

    return base_path


def _create_session_metadata(
    base_path: Path,
    session_id: str,
    session_type: str = "upload",
    created_by: str = "user",
    topic: Optional[str] = None
):
    """
    创建会话元数据文件

    Args:
        base_path: 会话目录路径
        session_id: 会话ID
        session_type: 会话类型 (upload, search, simulation, etc.)
        created_by: 创建方式 (user, system, api)
        topic: 会话主题（可选）
    """
    metadata_file = base_path / "session_metadata.json"

    # 如果元数据文件已存在，不覆盖
    if metadata_file.exists():
        logger.info(f"Session metadata already exists: {metadata_file}")
        return

    metadata = {
        "session_id": session_id,
        "topic": topic,
        "session_type": session_type,
        "created_by": created_by,
        "created_at": datetime.now().isoformat(),
        "folder_path": str(base_path),
        "folder_name": base_path.name
    }

    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"Created session metadata: {metadata_file}")
    except Exception as e:
        logger.error(f"Failed to create session metadata: {e}")


# 注：get_legacy_path() 和 migrate_legacy_data() 函数已删除
# 所有数据已迁移到新的 session_data 目录结构
# 如需手动迁移旧数据，请参考 docs/migration-guide.md（如有）


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
        elif data_type == "database":
            return f"/api/structures/{session_id}/database/{filename}"
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
