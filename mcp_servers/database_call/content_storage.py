"""
内容存储辅助模块 - 用于减少MCP工具返回值的上下文开销

功能：
1. 将大型CIF内容保存到文件
2. 返回文件路径引用而非完整内容
3. 提供内容摘要功能
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# 🔧 使用统一的路径管理模块
_MODULE_DIR = Path(__file__).parent.parent.parent  # ResearchMind根目录
utils_path = _MODULE_DIR / "utils"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

from utils.paths import session_data_root, ensure_dirs

# 数据存储目录 - 使用统一的 session_data 目录（位于 ../data/session_data）
SESSION_DATA_DIR = session_data_root()
STRUCTURES_DIR = SESSION_DATA_DIR / "structures"
METADATA_DIR = SESSION_DATA_DIR / "metadata"

# 注意：不再在模块加载时创建目录
# 目录会在实际保存文件时按需创建，避免产生空目录


def save_structure_to_file(
    structure_data: Dict[str, Any],
    session_id: str,
    database: str = "MP"
) -> str:
    """
    将结构数据保存到文件，返回文件路径
    
    Args:
        structure_data: 结构数据字典（包含cifContent等）
        session_id: 会话ID
        database: 数据库名称（MP, OQMD, COD等）
    
    Returns:
        文件路径
    """
    if not session_id:
        logger.warning("⚠️ session_id not provided, cannot save CIF")
        return ""
        
    try:
        # 🔧 使用 simulation/session_id/cif 目录，与其他 CIF 文件保持一致
        # 这样 simulation server 可以通过 _resolve_structure_path_by_source 找到这些文件
        try:
            shared_path = Path(__file__).parent.parent / "shared"
            if str(shared_path) not in sys.path:
                sys.path.insert(0, str(shared_path))
            from storage_manager import get_session_storage_path
            
            # 保存到 simulation/session_id/database 目录（数据库检索的结构单独存放）
            session_cif_dir = get_session_storage_path(
                session_id=session_id,
                data_type="database",  # 🆕 使用专门的 database 目录
                create=True
            )
        except Exception as e:
            logger.error(f"Failed to get session storage path: {e}")
            return "" # 🗑️ Removed legacy fallback to STRUCTURES_DIR
        
        # 生成文件名
        material_id = structure_data.get('material_id', 'unknown')
        formula = structure_data.get('formula_pretty', structure_data.get('name', 'unknown'))
        
        # 清理文件名中的非法字符
        import re
        safe_formula = re.sub(r'[<>:"/\\|?*]', '_', str(formula))
        safe_material_id = re.sub(r'[<>:"/\\|?*]', '_', str(material_id))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{database}_{safe_formula}_{safe_material_id}_{timestamp}.cif"
        
        # 保存CIF文件
        cif_content = structure_data.get('cifContent', '')
        if cif_content and cif_content != 'N/A':
            cif_path = session_cif_dir / filename
            with open(cif_path, 'w', encoding='utf-8') as f:
                f.write(cif_content)
            logger.info(f"💾 Saved CIF to: {cif_path}")
            return str(cif_path)
        
        return ""
    
    except Exception as e:
        logger.error(f"❌ Failed to save structure to file: {e}")
        return ""


def optimize_structure_data(
    structure_data: Dict[str, Any],
    session_id: str = None,
    save_cif: bool = True,
    database: str = "MP"  # 🆕 Added database parameter
) -> Dict[str, Any]:
    """
    优化结构数据，减少上下文开销
    
    Args:
        structure_data: 原始结构数据
        session_id: 会话ID（如果提供，则保存CIF到文件）
        save_cif: 是否保存CIF到文件
        database: 数据库名称
    
    Returns:
        优化后的结构数据（添加文件路径，保留CIF内容）
    """
    optimized = structure_data.copy()
    
    # 如果CIF内容较大，保存到文件（但保留 cifContent 供前端渲染）
    cif_content = optimized.get('cifContent', '')
    if cif_content and cif_content != 'N/A' and len(cif_content) > 500:
        if save_cif and session_id:
            # 保存到文件
            cif_path = save_structure_to_file(structure_data, session_id, database=database) # 🆕 Pass database
            if cif_path:
                optimized['cif_file_path'] = cif_path
                # 🆕 添加 cifFilename，使用保存的文件名
                import os
                optimized['cifFilename'] = os.path.basename(cif_path)
                # 🔧 修复：保留 cifContent 供前端 3D 渲染使用
                # 前端使用 cifContent 渲染结构，后端工具使用 cif_file_path
                logger.info(f"✅ CIF saved to {cif_path}, cifContent retained for frontend")
            else:
                # 🔧 保存失败，保留完整的 cifContent 以便前端显示
                logger.warning(f"⚠️ Failed to save CIF, keeping full content for frontend")
        # 🔧 不再删除 cifContent，因为前端需要它来渲染 3D 结构
        # 即使没有 session_id，也保留完整的 cifContent
    
    return optimized


def optimize_batch_results(
    results: Dict[str, Any],
    session_id: str = None,
    save_cif: bool = True
) -> Dict[str, Any]:
    """
    优化批量查询结果
    
    Args:
        results: 原始查询结果
        session_id: 会话ID
        save_cif: 是否保存CIF到文件
    
    Returns:
        优化后的结果
    """
    optimized = results.copy()
    
    # 🆕 Get database name from results
    database = optimized.get("database", "MP")
    
    # 优化structures列表
    if 'structures' in optimized and isinstance(optimized['structures'], list):
        optimized['structures'] = [
            optimize_structure_data(s, session_id, save_cif, database=database) # 🆕 Pass database
            for s in optimized['structures']
        ]
    
    # 添加优化信息
    optimized['optimization_info'] = {
        'cif_saved_to_files': save_cif and session_id is not None,
        'session_id': session_id,
        'timestamp': datetime.now().isoformat()
    }
    
    return optimized


def get_structure_summary(structure_data: Dict[str, Any]) -> str:
    """
    获取结构数据摘要
    
    Args:
        structure_data: 结构数据
    
    Returns:
        摘要字符串
    """
    material_id = structure_data.get('material_id', 'Unknown')
    formula = structure_data.get('formula_pretty', 'Unknown')
    symmetry = structure_data.get('symmetry', {})
    crystal_system = symmetry.get('crystal_system', 'Unknown') if symmetry else 'Unknown'
    
    return f"{formula} ({material_id}) - {crystal_system}"

