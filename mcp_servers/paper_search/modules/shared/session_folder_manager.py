"""
Session Folder Manager (会话文件夹管理器)

管理会话级别的文件夹，确保一次对话只使用一个文件夹保存所有内容。
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()

# 会话文件夹映射文件
SESSION_MAPPING_FILE = "./paper_search/session_folders.json"
PAPER_DIR = "./paper_search/papers"


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
    
    def get_session_folder(self, session_id: str, topic: Optional[str] = None) -> str:
        """
        获取会话文件夹路径
        
        Args:
            session_id: 会话ID
            topic: 主题（可选，用于文件夹命名）
        
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
        
        # 保存映射
        self.session_folders[session_id] = folder_path
        self._save_session_mapping()
        
        # 创建会话元数据文件
        self._create_session_metadata(folder_path, session_id, topic)
        
        logger.info(f"Created new folder for session {session_id}: {folder_path}")
        return folder_path
    
    def _generate_folder_name(self, session_id: str, topic: Optional[str] = None) -> str:
        """
        生成文件夹名称

        Args:
            session_id: 会话ID
            topic: 主题（可选）

        Returns:
            文件夹名称
        """
        # 直接使用session_id作为文件夹名
        # session_id已经包含了query和hash,格式: {query_clean}_{hash}
        # 例如: knowledge_graph_design_a1b2c3d4
        folder_name = session_id

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
    
    def _create_session_metadata(self, folder_path: str, session_id: str, topic: Optional[str] = None):
        """
        创建会话元数据文件
        
        Args:
            folder_path: 文件夹路径
            session_id: 会话ID
            topic: 主题（可选）
        """
        metadata = {
            "session_id": session_id,
            "topic": topic,
            "created_at": datetime.now().isoformat(),
            "folder_path": folder_path
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


def get_session_folder(session_id: str, topic: Optional[str] = None) -> str:
    """
    获取会话文件夹路径（便捷函数）
    
    Args:
        session_id: 会话ID
        topic: 主题（可选）
    
    Returns:
        文件夹路径
    """
    manager = get_session_folder_manager()
    return manager.get_session_folder(session_id, topic)


def cleanup_session(session_id: str):
    """
    清理会话（便捷函数）
    
    Args:
        session_id: 会话ID
    """
    manager = get_session_folder_manager()
    manager.cleanup_session(session_id)

