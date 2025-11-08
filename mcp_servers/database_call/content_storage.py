"""
内容存储辅助模块 - 用于减少MCP工具返回值的上下文开销

功能：
1. 将大型CIF内容保存到文件
2. 返回文件路径引用而非完整内容
3. 提供内容摘要功能
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# 数据存储目录 - 使用统一的 session_data 目录
_MODULE_DIR = Path(__file__).parent.parent.parent  # ResearchMind根目录
SESSION_DATA_DIR = _MODULE_DIR / "session_data"
STRUCTURES_DIR = SESSION_DATA_DIR / "structures"
METADATA_DIR = SESSION_DATA_DIR / "metadata"

# 确保目录存在
STRUCTURES_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)


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
    try:
        # 创建会话目录
        session_dir = STRUCTURES_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        material_id = structure_data.get('material_id', 'unknown')
        formula = structure_data.get('formula_pretty', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{database}_{formula}_{material_id}_{timestamp}.cif"
        
        # 保存CIF文件
        cif_content = structure_data.get('cifContent', '')
        if cif_content and cif_content != 'N/A':
            cif_path = session_dir / filename
            with open(cif_path, 'w', encoding='utf-8') as f:
                f.write(cif_content)
            logger.info(f"Saved CIF to: {cif_path}")
            return str(cif_path)
        
        return ""
    
    except Exception as e:
        logger.error(f"Failed to save structure to file: {e}")
        return ""


def optimize_structure_data(
    structure_data: Dict[str, Any],
    session_id: str = None,
    save_cif: bool = True
) -> Dict[str, Any]:
    """
    优化结构数据，减少上下文开销
    
    Args:
        structure_data: 原始结构数据
        session_id: 会话ID（如果提供，则保存CIF到文件）
        save_cif: 是否保存CIF到文件
    
    Returns:
        优化后的结构数据（CIF内容替换为文件路径或摘要）
    """
    optimized = structure_data.copy()
    
    # 如果CIF内容较大，保存到文件
    cif_content = optimized.get('cifContent', '')
    if cif_content and cif_content != 'N/A' and len(cif_content) > 500:
        if save_cif and session_id:
            # 保存到文件
            cif_path = save_structure_to_file(structure_data, session_id)
            if cif_path:
                optimized['cif_file_path'] = cif_path
                # 保留CIF摘要
                optimized['cif_summary'] = cif_content[:200] + f"... (saved to file, total {len(cif_content)} chars)"
                # 移除完整CIF内容
                del optimized['cifContent']
        else:
            # 不保存文件，只保留摘要
            optimized['cif_summary'] = cif_content[:200] + f"... (truncated, total {len(cif_content)} chars)"
            del optimized['cifContent']
    
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
    
    # 优化structures列表
    if 'structures' in optimized and isinstance(optimized['structures'], list):
        optimized['structures'] = [
            optimize_structure_data(s, session_id, save_cif)
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

