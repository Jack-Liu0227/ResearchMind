"""
Session Folder Manager (会话文件夹管理器)

管理会话级别的文件夹，确保一次对话只使用一个文件夹保存所有内容。
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import structlog

logger = structlog.get_logger()

# 会话文件夹映射文件
# 🔧 使用统一的 session_data 目录
# Note: Use absolute paths based on this module's location to ensure consistency
# regardless of where the server is started from
_MODULE_DIR = Path(__file__).parent.parent.parent  # mcp_servers/paper_search/
_ROOT_DIR = _MODULE_DIR.parent.parent  # ResearchMind根目录
SESSION_DATA_DIR = _ROOT_DIR / "session_data"
SESSION_MAPPING_FILE = str(SESSION_DATA_DIR / "paper_sessions.json")
PAPER_DIR = str(SESSION_DATA_DIR / "papers")

# 确保目录存在
SESSION_DATA_DIR.mkdir(parents=True, exist_ok=True)
Path(PAPER_DIR).mkdir(parents=True, exist_ok=True)


class SessionFolderManager:
    """会话文件夹管理器"""
    
    def __init__(self):
        """初始化会话文件夹管理器"""
        self.session_folders: Dict[str, str] = {}
        self._load_session_mapping()
    
    def _load_session_mapping(self):
        """加载会话文件夹映射"""
        try:
            if os.path.exists(SESSION_MAPPING_FILE):
                with open(SESSION_MAPPING_FILE, 'r', encoding='utf-8') as f:
                    self.session_folders = json.load(f)
                logger.info(f"Loaded session mapping: {len(self.session_folders)} sessions")
            else:
                self.session_folders = {}
                logger.info("No existing session mapping found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load session mapping: {e}")
            self.session_folders = {}
    
    def _save_session_mapping(self):
        """保存会话文件夹映射"""
        try:
            os.makedirs(os.path.dirname(SESSION_MAPPING_FILE), exist_ok=True)
            with open(SESSION_MAPPING_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.session_folders, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved session mapping: {len(self.session_folders)} sessions")
        except Exception as e:
            logger.error(f"Failed to save session mapping: {e}")
    
    def get_session_folder(
        self,
        session_id: str,
        topic: Optional[str] = None,
        session_type: str = 'search',
        created_by: str = 'system'
    ) -> str:
        """
        获取会话文件夹路径

        Args:
            session_id: 会话ID
            topic: 主题（可选，记录在元数据中）
            session_type: 会话类型 ('search', 'upload', 'test')
            created_by: 创建方式 ('system', 'user', 'api')

        Returns:
            文件夹路径
        """
        # 如果会话已有文件夹，直接返回
        if session_id in self.session_folders:
            folder_path = self.session_folders[session_id]
            logger.info(f"Using existing folder for session {session_id}: {folder_path}")
            return folder_path

        # 创建新文件夹
        folder_name = self._generate_folder_name(session_id, topic)
        folder_path = os.path.join(PAPER_DIR, folder_name)

        # 创建文件夹
        os.makedirs(folder_path, exist_ok=True)

        # 保存映射（使用 session_id 作为 key，folder_path 作为 value）
        self.session_folders[session_id] = folder_path
        self._save_session_mapping()

        # 创建会话元数据文件
        self._create_session_metadata(
            folder_path,
            session_id,
            topic,
            session_type=session_type,
            created_by=created_by
        )

        logger.info(f"Created new folder for session {session_id}: {folder_path}")
        return folder_path
    
    def _generate_folder_name(self, session_id: str, topic: Optional[str] = None) -> str:
        """
        生成文件夹名称

        统一使用 session_{timestamp}_{random_id} 格式
        例如: session_1763305049955_zs3m2y8m

        Args:
            session_id: 会话ID
            topic: 主题（可选，不用于文件夹命名）

        Returns:
            文件夹名称
        """
        import time
        import random
        import string

        # 检查 session_id 是否已经是 session_{timestamp}_{id} 格式
        if session_id.startswith('session_'):
            # 已经是正确格式，直接使用
            folder_name = session_id
        else:
            # 生成新的 session 格式文件夹名
            timestamp = int(time.time() * 1000)  # 毫秒级时间戳
            random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            folder_name = f"session_{timestamp}_{random_id}"

            logger.info(f"Generated session folder name: {folder_name} for session_id: {session_id}")

        return folder_name
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
        
        Returns:
            清理后的文件名
        """
        import re
        # 移除非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除多余的空格和下划线
        filename = re.sub(r'[\s_]+', '_', filename)
        # 移除首尾的下划线
        filename = filename.strip('_')
        return filename
    
    def _create_session_metadata(
        self,
        folder_path: str,
        session_id: str,
        topic: Optional[str] = None,
        session_type: str = 'search',
        created_by: str = 'system'
    ):
        """
        创建会话元数据文件

        Args:
            folder_path: 文件夹路径
            session_id: 会话ID
            topic: 主题（可选）
            session_type: 会话类型 ('search', 'upload', 'test')
            created_by: 创建方式 ('system', 'user', 'api')
        """
        metadata = {
            "session_id": session_id,
            "topic": topic,
            "session_type": session_type,
            "created_by": created_by,
            "created_at": datetime.now().isoformat(),
            "folder_path": folder_path,
            "folder_name": os.path.basename(folder_path)
        }

        metadata_file = os.path.join(folder_path, "session_metadata.json")
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Created session metadata: {metadata_file}")
        except Exception as e:
            logger.error(f"Failed to create session metadata: {e}")
    
    def get_folder_for_session(self, session_id: str) -> Optional[str]:
        """
        获取会话的文件夹路径（不创建新文件夹）
        
        Args:
            session_id: 会话ID
        
        Returns:
            文件夹路径，如果不存在返回 None
        """
        return self.session_folders.get(session_id)
    
    def cleanup_session(self, session_id: str):
        """
        清理会话（从映射中移除，但不删除文件夹）
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.session_folders:
            folder_path = self.session_folders[session_id]
            del self.session_folders[session_id]
            self._save_session_mapping()
            logger.info(f"Cleaned up session {session_id}, folder: {folder_path}")
    
    def list_sessions(self) -> Dict[str, str]:
        """
        列出所有会话
        
        Returns:
            会话ID到文件夹路径的映射
        """
        return self.session_folders.copy()


# 全局会话文件夹管理器实例
_session_folder_manager: Optional[SessionFolderManager] = None


def get_session_folder_manager() -> SessionFolderManager:
    """
    获取全局会话文件夹管理器实例
    
    Returns:
        SessionFolderManager 实例
    """
    global _session_folder_manager
    if _session_folder_manager is None:
        _session_folder_manager = SessionFolderManager()
    return _session_folder_manager


def get_session_folder(
    session_id: str,
    topic: Optional[str] = None,
    session_type: str = 'search',
    created_by: str = 'system'
) -> str:
    """
    获取会话文件夹路径（便捷函数）

    Args:
        session_id: 会话ID
        topic: 主题（可选，记录在元数据中）
        session_type: 会话类型 ('search', 'upload', 'test')
        created_by: 创建方式 ('system', 'user', 'api')

    Returns:
        文件夹路径
    """
    manager = get_session_folder_manager()
    return manager.get_session_folder(session_id, topic, session_type, created_by)


def cleanup_session(session_id: str):
    """
    清理会话（便捷函数）

    Args:
        session_id: 会话ID
    """
    manager = get_session_folder_manager()
    manager.cleanup_session(session_id)


# ============================================================================
# 内容存储辅助函数 - 用于减少上下文开销
# ============================================================================

def save_content_to_file(
    content: str,
    session_id: str,
    filename: str,
    subfolder: str = "content"
) -> str:
    """
    将大型内容保存到文件，返回文件路径

    Args:
        content: 要保存的内容
        session_id: 会话ID
        filename: 文件名
        subfolder: 子文件夹名称（默认: content）

    Returns:
        文件的绝对路径
    """
    try:
        # 获取会话文件夹
        session_folder = get_session_folder(session_id)

        # 创建子文件夹
        content_dir = os.path.join(session_folder, subfolder)
        os.makedirs(content_dir, exist_ok=True)

        # 保存文件
        file_path = os.path.join(content_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Saved content to file: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Failed to save content to file: {e}")
        raise


def load_content_from_file(file_path: str) -> str:
    """
    从文件加载内容

    Args:
        file_path: 文件路径

    Returns:
        文件内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Loaded content from file: {file_path}")
        return content

    except Exception as e:
        logger.error(f"Failed to load content from file: {e}")
        raise


def get_content_summary(content: str, max_length: int = 500) -> str:
    """
    获取内容摘要（用于返回给上下文）

    Args:
        content: 完整内容
        max_length: 最大长度

    Returns:
        内容摘要
    """
    if len(content) <= max_length:
        return content

    return content[:max_length] + f"... (truncated, total {len(content)} chars)"

