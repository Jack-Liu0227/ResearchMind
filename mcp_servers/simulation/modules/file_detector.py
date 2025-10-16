"""
File Detector Module
Detects and analyzes file uploads in user messages
"""
import base64
import re
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


def detect_files_in_message_impl(message_parts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect if user has uploaded any files in the message.

    This function analyzes message parts to identify file uploads,
    extract file information, and provide a summary.

    Args:
        message_parts: List of message parts from user message
                      Expected structure: [{"resource": {"name": "...", "blob": {"data": "..."}}}]

    Returns:
        Dict containing:
        - has_files: bool - Whether files were detected
        - file_count: int - Number of files detected
        - files: List[Dict] - Information about each file
        - summary: str - Human-readable summary
        - cif_files: List[Dict] - CIF files specifically
        - other_files: List[Dict] - Non-CIF files
    """
    try:
        logger.info("Detecting files in message",
                   parts_count=len(message_parts),
                   parts_type=type(message_parts).__name__)

        # DEBUG: Log the actual structure
        logger.info("Message parts structure",
                   parts_repr=str(message_parts)[:500])  # First 500 chars

        detected_files = []
        cif_files = []
        other_files = []

        # Analyze each part
        for idx, part in enumerate(message_parts):
            logger.info("Analyzing part",
                       index=idx,
                       part_type=type(part).__name__,
                       part_keys=list(part.keys()) if isinstance(part, dict) else "not_dict")

            if not isinstance(part, dict):
                continue

            # Check for resource (file upload)
            if "resource" in part:
                resource = part["resource"]
                logger.info("Found resource",
                           resource_keys=list(resource.keys()) if isinstance(resource, dict) else "not_dict")
                file_info = _analyze_resource(resource, idx)

                if file_info:
                    detected_files.append(file_info)

                    # Categorize by file type
                    if file_info['is_cif']:
                        cif_files.append(file_info)
                    else:
                        other_files.append(file_info)
        
        # Generate summary
        has_files = len(detected_files) > 0
        summary = _generate_summary(detected_files, cif_files, other_files)
        
        result = {
            "has_files": has_files,
            "file_count": len(detected_files),
            "files": detected_files,
            "cif_files": cif_files,
            "other_files": other_files,
            "summary": summary,
            "success": True
        }
        
        if has_files:
            logger.info("Files detected", 
                       file_count=len(detected_files),
                       cif_count=len(cif_files),
                       other_count=len(other_files))
        else:
            logger.info("No files detected in message")
        
        return result
        
    except Exception as e:
        logger.error("File detection failed", error=str(e))
        return {
            "has_files": False,
            "file_count": 0,
            "files": [],
            "cif_files": [],
            "other_files": [],
            "summary": "文件检测失败",
            "success": False,
            "error": str(e)
        }


def _analyze_resource(resource: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
    """
    Analyze a resource object to extract file information.
    
    Args:
        resource: Resource dictionary from message part
        index: Index of the part in the message
    
    Returns:
        Dict with file information or None if not a valid file
    """
    try:
        # Extract filename
        filename = resource.get("name", f"file_{index}")
        
        # Extract content
        content = None
        content_type = None
        is_base64 = False
        
        if "blob" in resource and "data" in resource["blob"]:
            content = resource["blob"]["data"]
            content_type = "blob"
            is_base64 = True
        elif "text" in resource:
            content = resource["text"]
            content_type = "text"
            is_base64 = False
        
        if not content:
            return None
        
        # Analyze content
        file_extension = _get_file_extension(filename)
        is_cif = _is_cif_file(filename, content, is_base64)
        content_preview = _get_content_preview(content, is_base64)
        estimated_size = _estimate_size(content, is_base64)
        
        return {
            "filename": filename,
            "extension": file_extension,
            "is_cif": is_cif,
            "content_type": content_type,
            "is_base64": is_base64,
            "estimated_size_bytes": estimated_size,
            "estimated_size_kb": round(estimated_size / 1024, 2),
            "content_preview": content_preview,
            "index": index
        }
        
    except Exception as e:
        logger.error("Resource analysis failed", error=str(e), index=index)
        return None


def _get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    if '.' in filename:
        return filename.rsplit('.', 1)[-1].lower()
    return ""


def _is_cif_file(filename: str, content: str, is_base64: bool) -> bool:
    """
    Determine if a file is a CIF file.
    
    Checks:
    1. File extension (.cif)
    2. Content starts with 'data_' (CIF format)
    """
    # Check extension
    if filename.lower().endswith('.cif'):
        return True
    
    # Check content
    try:
        # Decode if base64
        if is_base64:
            try:
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                content = decoded
            except:
                pass
        
        # Check for CIF markers
        content_lower = content.lower().strip()
        if content_lower.startswith('data_'):
            return True
        
        # Check for common CIF keywords
        cif_keywords = ['_cell_length', '_atom_site', 'loop_', '_symmetry']
        if any(keyword in content_lower for keyword in cif_keywords):
            return True
        
    except Exception as e:
        logger.debug("CIF content check failed", error=str(e))
    
    return False


def _get_content_preview(content: str, is_base64: bool, max_length: int = 100) -> str:
    """Get a preview of the file content."""
    try:
        if is_base64:
            # Try to decode for preview
            try:
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                preview = decoded[:max_length]
            except:
                preview = "[Binary content]"
        else:
            preview = content[:max_length]
        
        if len(content) > max_length:
            preview += "..."
        
        return preview
        
    except Exception:
        return "[Preview unavailable]"


def _estimate_size(content: str, is_base64: bool) -> int:
    """Estimate file size in bytes."""
    if is_base64:
        # Base64 encoded size is ~4/3 of original
        return int(len(content) * 3 / 4)
    else:
        # Text content
        return len(content.encode('utf-8'))


def _generate_summary(all_files: List[Dict], cif_files: List[Dict], other_files: List[Dict]) -> str:
    """Generate a human-readable summary of detected files."""
    if not all_files:
        return "未检测到文件上传"
    
    summary_parts = []
    
    # Overall count
    summary_parts.append(f"✅ 检测到 {len(all_files)} 个文件")
    
    # CIF files
    if cif_files:
        cif_names = [f['filename'] for f in cif_files]
        summary_parts.append(f"\n📄 CIF 文件 ({len(cif_files)} 个):")
        for name in cif_names:
            summary_parts.append(f"  - {name}")
    
    # Other files
    if other_files:
        other_names = [f['filename'] for f in other_files]
        summary_parts.append(f"\n📎 其他文件 ({len(other_files)} 个):")
        for name in other_names:
            summary_parts.append(f"  - {name}")
    
    # Size info
    total_size_kb = sum(f['estimated_size_kb'] for f in all_files)
    summary_parts.append(f"\n💾 总大小: {total_size_kb:.2f} KB")
    
    return "".join(summary_parts)


# Export the implementation
__all__ = ["detect_files_in_message_impl"]

