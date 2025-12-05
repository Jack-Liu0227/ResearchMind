"""
Report Version Manager (报告版本管理器)

功能：
1. 版本保存 - 为每个报告生成唯一版本号
2. 版本列表 - 列出所有历史版本
3. 版本加载 - 加载指定版本的报告
4. 版本删除 - 删除指定版本
5. 版本对比 - 对比不同版本的差异（可选）

版本号格式：v{序号}_{时间戳}_{UUID前6位}
例如：v1_20241205_150000_abc123
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)

# 🔧 使用统一的配置路径
# 添加 paper_search 目录到 sys.path
import sys
from pathlib import Path as PathLib
_CURRENT_FILE = PathLib(__file__)
_PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
if str(_PAPER_SEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(_PAPER_SEARCH_DIR))

from config import REPORTS_DIR


class ReportVersionManager:
    """报告版本管理器"""
    
    def __init__(self, session_id: str = "default"):
        """
        初始化版本管理器
        
        Args:
            session_id: 会话ID（用于组织不同会话的报告）
        """
        self.session_id = session_id
        self.session_dir = REPORTS_DIR / session_id
        self.versions_file = self.session_dir / "versions.json"
        
        # 确保目录存在
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载或初始化版本元数据
        self._load_versions_metadata()
        
        logger.info(f"ReportVersionManager initialized for session: {session_id}")
    
    def _load_versions_metadata(self):
        """加载版本元数据"""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    self.versions_metadata = json.load(f)
                logger.info(f"Loaded {len(self.versions_metadata)} versions from metadata file")
            except Exception as e:
                logger.error(f"Failed to load versions metadata: {e}")
                self.versions_metadata = []
        else:
            self.versions_metadata = []
            logger.info("No existing versions metadata found, starting fresh")
    
    def _save_versions_metadata(self):
        """保存版本元数据"""
        try:
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(self.versions_metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.versions_metadata)} versions to metadata file")
        except Exception as e:
            logger.error(f"Failed to save versions metadata: {e}")
            raise
    
    def _generate_version_id(self) -> Tuple[str, str]:
        """
        生成版本ID和文件名
        
        Returns:
            Tuple[version_id, filename]
            - version_id: 版本号（如 "v1_20241205_150000_abc123"）
            - filename: 文件名（如 "v1_20241205_150000_abc123.md"）
        """
        # 获取下一个版本序号
        version_number = len(self.versions_metadata) + 1
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成UUID前6位
        uuid_prefix = str(uuid.uuid4())[:6]
        
        # 组合版本ID
        version_id = f"v{version_number}_{timestamp}_{uuid_prefix}"
        filename = f"{version_id}.md"
        
        return version_id, filename
    
    def save_report_version(
        self,
        report_content: str,
        topic: str,
        papers_count: int,
        analysis_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        保存新版本的报告
        
        Args:
            report_content: 报告内容（Markdown格式）
            topic: 研究主题
            papers_count: 论文数量
            analysis_params: 分析参数（可选）
            metadata: 额外的元数据（可选）
        
        Returns:
            Dict containing version information
        """
        try:
            # 生成版本ID和文件名
            version_id, filename = self._generate_version_id()
            file_path = self.session_dir / filename
            
            # 保存报告内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # 创建版本元数据
            version_metadata = {
                'version_id': version_id,
                'filename': filename,
                'file_path': str(file_path),
                'topic': topic,
                'papers_count': papers_count,
                'created_at': datetime.now().isoformat(),
                'analysis_params': analysis_params or {},
                'file_size': len(report_content.encode('utf-8')),
                'metadata': metadata or {}
            }
            
            # 添加到版本列表
            self.versions_metadata.append(version_metadata)
            
            # 保存元数据
            self._save_versions_metadata()
            
            logger.info(f"Saved report version: {version_id}")
            return version_metadata

        except Exception as e:
            logger.error(f"Failed to save report version: {e}")
            raise

    def list_report_versions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        列出所有报告版本

        Args:
            limit: 限制返回的版本数量（可选，None表示返回所有）

        Returns:
            List of version metadata dictionaries (按时间倒序)
        """
        # 按创建时间倒序排序
        sorted_versions = sorted(
            self.versions_metadata,
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )

        if limit:
            sorted_versions = sorted_versions[:limit]

        logger.info(f"Listed {len(sorted_versions)} report versions")
        return sorted_versions

    def load_report_version(self, version_id: str) -> Optional[str]:
        """
        加载指定版本的报告

        Args:
            version_id: 版本ID

        Returns:
            报告内容（Markdown格式），如果版本不存在则返回 None
        """
        try:
            # 查找版本元数据
            version_meta = None
            for meta in self.versions_metadata:
                if meta['version_id'] == version_id:
                    version_meta = meta
                    break

            if not version_meta:
                logger.warning(f"Version not found: {version_id}")
                return None

            # 读取报告文件
            file_path = Path(version_meta['file_path'])
            if not file_path.exists():
                logger.error(f"Report file not found: {file_path}")
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            logger.info(f"Loaded report version: {version_id}")
            return content

        except Exception as e:
            logger.error(f"Failed to load report version {version_id}: {e}")
            return None

    def get_version_metadata(self, version_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定版本的元数据

        Args:
            version_id: 版本ID

        Returns:
            版本元数据字典，如果版本不存在则返回 None
        """
        for meta in self.versions_metadata:
            if meta['version_id'] == version_id:
                return meta

        logger.warning(f"Version metadata not found: {version_id}")
        return None

    def delete_report_version(self, version_id: str) -> bool:
        """
        删除指定版本的报告

        Args:
            version_id: 版本ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # 查找版本元数据
            version_meta = None
            version_index = -1
            for i, meta in enumerate(self.versions_metadata):
                if meta['version_id'] == version_id:
                    version_meta = meta
                    version_index = i
                    break

            if not version_meta:
                logger.warning(f"Version not found: {version_id}")
                return False

            # 删除报告文件
            file_path = Path(version_meta['file_path'])
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted report file: {file_path}")

            # 从元数据列表中移除
            self.versions_metadata.pop(version_index)

            # 保存更新后的元数据
            self._save_versions_metadata()

            logger.info(f"Deleted report version: {version_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete report version {version_id}: {e}")
            return False

    def get_latest_report(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        获取最新版本的报告

        Returns:
            Tuple[report_content, version_metadata] if exists, None otherwise
        """
        if not self.versions_metadata:
            logger.info("No report versions found")
            return None

        # 获取最新版本
        latest_versions = self.list_report_versions(limit=1)
        if not latest_versions:
            return None

        latest_meta = latest_versions[0]
        version_id = latest_meta['version_id']

        # 加载报告内容
        content = self.load_report_version(version_id)
        if content is None:
            return None

        logger.info(f"Retrieved latest report: {version_id}")
        return (content, latest_meta)

    def get_version_count(self) -> int:
        """
        获取版本总数

        Returns:
            版本总数
        """
        return len(self.versions_metadata)

    def compare_versions(self, version_id_1: str, version_id_2: str) -> Optional[Dict[str, Any]]:
        """
        对比两个版本的差异（简化版）

        Args:
            version_id_1: 第一个版本ID
            version_id_2: 第二个版本ID

        Returns:
            Dict containing comparison results, None if versions not found
        """
        try:
            # 加载两个版本的内容
            content_1 = self.load_report_version(version_id_1)
            content_2 = self.load_report_version(version_id_2)

            if content_1 is None or content_2 is None:
                logger.warning(f"Cannot compare: one or both versions not found")
                return None

            # 获取元数据
            meta_1 = self.get_version_metadata(version_id_1)
            meta_2 = self.get_version_metadata(version_id_2)

            # 简单的差异统计
            comparison = {
                'version_1': {
                    'version_id': version_id_1,
                    'created_at': meta_1.get('created_at'),
                    'papers_count': meta_1.get('papers_count'),
                    'file_size': meta_1.get('file_size'),
                    'content_length': len(content_1)
                },
                'version_2': {
                    'version_id': version_id_2,
                    'created_at': meta_2.get('created_at'),
                    'papers_count': meta_2.get('papers_count'),
                    'file_size': meta_2.get('file_size'),
                    'content_length': len(content_2)
                },
                'differences': {
                    'size_diff': meta_2.get('file_size', 0) - meta_1.get('file_size', 0),
                    'papers_diff': meta_2.get('papers_count', 0) - meta_1.get('papers_count', 0),
                    'content_identical': content_1 == content_2
                }
            }

            logger.info(f"Compared versions: {version_id_1} vs {version_id_2}")
            return comparison

        except Exception as e:
            logger.error(f"Failed to compare versions: {e}")
            return None


# ============================================================================
# 全局单例管理器（便于使用）
# ============================================================================

_version_managers: Dict[str, ReportVersionManager] = {}


def get_version_manager(session_id: str = "default") -> ReportVersionManager:
    """
    获取版本管理器实例（单例模式）

    Args:
        session_id: 会话ID

    Returns:
        ReportVersionManager instance
    """
    if session_id not in _version_managers:
        _version_managers[session_id] = ReportVersionManager(session_id)

    return _version_managers[session_id]

