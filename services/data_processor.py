"""
Data Processor

Processes data from MCP tool results and prepares it for frontend transmission.
Handles structure data, image data, and other result types.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .structure_converter import StructureConverter
from .image_handler import ImageHandler
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class DataProcessor:
    """Process MCP tool results and prepare data for frontend"""

    # Maximum number of structures to keep in frontend
    MAX_STRUCTURES = 5

    @staticmethod
    async def process_tool_result(
        result: Any,
        agent_id: str,
        websocket: Any,
        session_id: Optional[str] = None
    ) -> Tuple[bool, bool]:
        """
        Process MCP tool result and send data to frontend

        Args:
            result: Tool result from MCP
            agent_id: Agent ID that generated the result
            websocket: WebSocket connection
            session_id: Session ID for data isolation

        Returns:
            Tuple of (structures_sent, images_sent)
        """
        structures_sent = False
        images_sent = False
        
        try:
            # Convert result to dict if needed
            if hasattr(result, 'to_dict'):
                data = result.to_dict()
            elif hasattr(result, '__dict__'):
                data = result.__dict__
            elif isinstance(result, dict):
                data = result
            else:
                logger.warning(f"⚠️ Unsupported result type: {type(result)}")
                return structures_sent, images_sent
            
            logger.info(f"🔍 Processing tool result with keys: {list(data.keys())}")

            # Send status update: working
            await DataProcessor._send_message(websocket, "status", {
                "status": "working",
                "message": "正在处理数据..."
            })

            # Process structure data
            structures_sent = await DataProcessor._process_structures(data, agent_id, websocket, session_id)

            # Process image data
            images_sent = await DataProcessor._process_images(data, agent_id, websocket, session_id)

            # Process file links (CSV and MD files from paper_search MCP)
            await DataProcessor._process_file_links(data, agent_id, websocket, session_id)

        except Exception as e:
            logger.error(f"❌ Failed to process tool result: {e}", exc_info=True)

        return structures_sent, images_sent
    
    @staticmethod
    async def _process_structures(
        data: Dict[str, Any],
        agent_id: str,
        websocket: Any,
        session_id: Optional[str] = None
    ) -> bool:
        """Process and send structure data"""
        try:
            # Extract structures using StructureConverter
            structures = StructureConverter.extract_structures_from_tool_result(data)

            if structures:
                logger.info(f"🗄️ Preparing to send {len(structures)} structures")

                # Update session structure count
                if session_id:
                    for _ in structures:
                        SessionManager.increment_structure_count(session_id)

                # Send all structures to frontend
                # Frontend will handle limiting display to MAX_STRUCTURES
                await DataProcessor._send_message(websocket, "structure_data", {
                    "structures": structures,
                    "agentId": agent_id,
                    "sessionId": session_id,  # Include session_id
                    "timestamp": datetime.now().isoformat(),
                    "total": len(structures),
                    "max_display": DataProcessor.MAX_STRUCTURES  # Hint for frontend
                })

                # Determine database name for logging
                db_name = DataProcessor._get_database_name(data)
                logger.info(f"✅ [Database:{db_name}] Sent {len(structures)} structures (session: {session_id})")

                return True
            else:
                logger.debug("No structures found in tool result")
                return False

        except Exception as e:
            logger.error(f"Failed to process structures: {e}")
            return False
    
    @staticmethod
    async def _process_images(
        data: Dict[str, Any],
        agent_id: str,
        websocket: Any,
        session_id: Optional[str] = None
    ) -> bool:
        """Process and send image data"""
        try:
            # Extract images using ImageHandler
            images = ImageHandler.extract_images_from_tool_result(data)

            if images:
                logger.info(f"🖼️ Preparing to send {len(images)} images")

                # Log image details
                for img in images:
                    logger.info(f"🖼️ Image: {img.get('name', 'no-name')} -> {img.get('url', 'no-url')}")

                # Update session image count
                if session_id:
                    for _ in images:
                        SessionManager.increment_image_count(session_id)

                # Create standardized response
                image_response = ImageHandler.create_image_list_response(images, agent_id)

                # Add session_id to response
                if session_id:
                    image_response["sessionId"] = session_id

                # Send to frontend
                await DataProcessor._send_message(websocket, "image_data", image_response)

                logger.info(f"✅ Sent {len(images)} images to frontend (session: {session_id})")

                return True
            else:
                logger.debug("No images found in tool result")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process images: {e}")
            return False
    
    @staticmethod
    async def _process_file_links(
        data: Dict[str, Any],
        agent_id: str,
        websocket: Any,
        session_id: Optional[str] = None
    ) -> bool:
        """Process and send file download links (CSV and MD files)"""
        try:
            file_metadata = {}

            # Extract CSV download URL
            if 'csv_download_url' in data:
                file_metadata['csv_download_url'] = data['csv_download_url']
                if 'csv_file_path' in data:
                    file_metadata['csv_file_path'] = data['csv_file_path']
                    inline_csv = DataProcessor._read_text_file(data['csv_file_path'])
                    if inline_csv is not None:
                        file_metadata['csv_inline_content'] = inline_csv
                logger.info(f"📄 Found CSV file: {data['csv_download_url']}")

            # Extract MD download URL
            if 'md_download_url' in data:
                file_metadata['md_download_url'] = data['md_download_url']
                if 'summary_file_path' in data:
                    file_metadata['summary_file_path'] = data['summary_file_path']
                    inline_md = DataProcessor._read_text_file(data['summary_file_path'])
                    if inline_md is not None:
                        file_metadata['md_inline_content'] = inline_md
                elif 'report_file_path' in data:
                    file_metadata['report_file_path'] = data['report_file_path']
                    inline_md = DataProcessor._read_text_file(data['report_file_path'])
                    if inline_md is not None:
                        file_metadata['md_inline_content'] = inline_md
                logger.info(f"📄 Found MD file: {data['md_download_url']}")

            # 🆕 处理热导率计算结果的 CSV 文件
            # 单个热导率计算
            if 'results_file' in data and data['results_file']:
                csv_path = data['results_file']
                filename = os.path.basename(csv_path)

                # 🔧 提取 CIF 文件名用于更清晰的显示
                cif_filename = data.get('cif_filename', '')
                method = data.get('method', 'unknown')
                kappa_value = data.get('thermal_conductivity', {}).get('value', 'N/A')

                # 生成更清晰的文件名：包含 CIF 名称、方法和热导率值
                if cif_filename:
                    display_name = f"{cif_filename} - {method} (κ={kappa_value} W/m·K)"
                else:
                    display_name = f"热导率结果 - {filename}"

                # 🔧 修复：从路径中提取 session_id 生成正确的 URL
                # 路径格式: session_data/simulation/{session_id}/thermal_conductivity/file.csv
                # URL 格式: /api/files/thermal_conductivity/{session_id}/thermal_conductivity/file.csv
                normalized_path = csv_path.replace('\\', '/')
                if 'session_data/simulation/' in normalized_path:
                    # 提取 session_data/simulation/ 后面的部分
                    relative_part = normalized_path.split('session_data/simulation/', 1)[1]
                    # relative_part 格式: {session_id}/thermal_conductivity/file.csv
                    csv_url = f"/api/files/thermal_conductivity/{relative_part}"
                    logger.info(f"🔗 Generated thermal conductivity URL from session_data path: {csv_url}")
                elif session_id:
                    # 如果有 session_id，使用它构建 URL
                    csv_url = f"/api/files/thermal_conductivity/{session_id}/thermal_conductivity/{filename}"
                    logger.info(f"🔗 Generated thermal conductivity URL with session_id: {csv_url}")
                else:
                    # 后备方案：只使用文件名（可能不工作）
                    csv_url = f"/api/files/thermal_conductivity/{filename}"
                    logger.warning(f"⚠️ Could not extract session_id from path, using filename only: {csv_url}")

                file_metadata['kappa_results_csv_url'] = csv_url
                file_metadata['kappa_results_csv_path'] = csv_path

                # 读取 CSV 内容用于内联展示
                inline_csv = DataProcessor._read_text_file(csv_path)
                if inline_csv is not None:
                    file_metadata['kappa_results_csv_content'] = inline_csv

                logger.info(f"📄 Found thermal conductivity results CSV: {csv_url}")

                # 🔧 同时发送为独立的文件数据，确保在右侧面板显示
                await DataProcessor._send_message(websocket, "file_data", {
                    "files": [{
                        "id": f"kappa_{filename}",
                        "type": "csv",
                        "name": display_name,
                        "downloadUrl": csv_url,
                        "filePath": csv_path,
                        "inlineContent": inline_csv,
                        "createdAt": datetime.now().timestamp() * 1000,
                        "extra": {
                            "category": "thermal_conductivity",
                            "cif_filename": cif_filename,
                            "method": method,
                            "kappa_value": kappa_value
                        }
                    }],
                    "agentId": agent_id,
                    "sessionId": session_id,
                    "timestamp": datetime.now().isoformat()
                })

            # 批量热导率计算
            if 'batch_results_file' in data and data['batch_results_file']:
                csv_path = data['batch_results_file']
                filename = os.path.basename(csv_path)

                # 🔧 修复：从路径中提取 session_id 生成正确的 URL
                normalized_path = csv_path.replace('\\', '/')
                if 'session_data/simulation/' in normalized_path:
                    relative_part = normalized_path.split('session_data/simulation/', 1)[1]
                    csv_url = f"/api/files/thermal_conductivity/{relative_part}"
                    logger.info(f"🔗 Generated batch thermal conductivity URL from session_data path: {csv_url}")
                elif session_id:
                    csv_url = f"/api/files/thermal_conductivity/{session_id}/thermal_conductivity/{filename}"
                    logger.info(f"🔗 Generated batch thermal conductivity URL with session_id: {csv_url}")
                else:
                    csv_url = f"/api/files/thermal_conductivity/{filename}"
                    logger.warning(f"⚠️ Could not extract session_id from path, using filename only: {csv_url}")

                file_metadata['kappa_batch_csv_url'] = csv_url
                file_metadata['kappa_batch_csv_path'] = csv_path

                # 读取 CSV 内容用于内联展示
                inline_csv = DataProcessor._read_text_file(csv_path)
                if inline_csv is not None:
                    file_metadata['kappa_batch_csv_content'] = inline_csv

                logger.info(f"📄 Found batch thermal conductivity results CSV: {csv_url}")

                # 🔧 同时发送为独立的文件数据，确保在右侧面板显示
                await DataProcessor._send_message(websocket, "file_data", {
                    "files": [{
                        "id": f"kappa_batch_{filename}",
                        "type": "csv",
                        "name": f"批量热导率结果 - {filename}",
                        "downloadUrl": csv_url,
                        "filePath": csv_path,
                        "inlineContent": inline_csv,
                        "createdAt": datetime.now().timestamp() * 1000,
                        "extra": {
                            "category": "thermal_conductivity_batch",
                            "method": data.get('method', 'unknown')
                        }
                    }],
                    "agentId": agent_id,
                    "sessionId": session_id,
                    "timestamp": datetime.now().isoformat()
                })

            # 🆕 处理声子计算结果的 CSV 文件
            # 声子色散数据
            if 'phonon_dispersion_csv' in data and data['phonon_dispersion_csv']:
                csv_path = data['phonon_dispersion_csv']
                filename = os.path.basename(csv_path)

                # 🔧 修复：从路径中提取 session_id 生成正确的 URL
                # 路径格式: session_data/simulation/{session_id}/phonon_results/file.csv
                # URL 格式: /api/images/phonon/{session_id}/phonon_results/file.csv
                normalized_path = csv_path.replace('\\', '/')
                if 'session_data/simulation/' in normalized_path:
                    # 提取 session_data/simulation/ 后面的部分
                    relative_part = normalized_path.split('session_data/simulation/', 1)[1]
                    # relative_part 格式: {session_id}/phonon_results/file.csv
                    csv_url = f"/api/images/phonon/{relative_part}"
                    logger.info(f"🔗 Generated phonon dispersion CSV URL from session_data path: {csv_url}")
                elif session_id:
                    # 如果有 session_id，使用它构建 URL
                    csv_url = f"/api/images/phonon/{session_id}/phonon_results/{filename}"
                    logger.info(f"🔗 Generated phonon dispersion CSV URL with session_id: {csv_url}")
                else:
                    # 后备方案：只使用文件名（可能不工作）
                    csv_url = f"/api/images/phonon/{filename}"
                    logger.warning(f"⚠️ Could not extract session_id from path, using filename only: {csv_url}")

                file_metadata['phonon_dispersion_csv_url'] = csv_url
                file_metadata['phonon_dispersion_csv_path'] = csv_path

                # 🔧 优化：不传输完整 CSV 内容，只传递下载 URL
                # 前端可以通过 URL 按需下载 CSV 文件
                # inline_csv = DataProcessor._read_text_file(csv_path)
                # if inline_csv is not None:
                #     file_metadata['phonon_dispersion_csv_content'] = inline_csv

                logger.info(f"📄 Found phonon dispersion CSV: {csv_url}")

                # 🔧 同时发送为独立的文件数据，确保在右侧面板显示
                await DataProcessor._send_message(websocket, "file_data", {
                    "files": [{
                        "id": f"phonon_dispersion_{filename}",
                        "type": "csv",
                        "name": f"声子色散数据 - {filename}",
                        "downloadUrl": csv_url,
                        "filePath": csv_path,
                        "createdAt": datetime.now().timestamp() * 1000,
                        "extra": {
                            "category": "phonon_dispersion"
                        }
                    }],
                    "agentId": agent_id,
                    "sessionId": session_id,
                    "timestamp": datetime.now().isoformat()
                })

            # 声子态密度数据
            if 'phonon_dos_csv' in data and data['phonon_dos_csv']:
                csv_path = data['phonon_dos_csv']
                filename = os.path.basename(csv_path)

                # 🔧 修复：从路径中提取 session_id 生成正确的 URL
                normalized_path = csv_path.replace('\\', '/')
                if 'session_data/simulation/' in normalized_path:
                    relative_part = normalized_path.split('session_data/simulation/', 1)[1]
                    csv_url = f"/api/images/phonon/{relative_part}"
                    logger.info(f"🔗 Generated phonon DOS CSV URL from session_data path: {csv_url}")
                elif session_id:
                    csv_url = f"/api/images/phonon/{session_id}/phonon_results/{filename}"
                    logger.info(f"🔗 Generated phonon DOS CSV URL with session_id: {csv_url}")
                else:
                    csv_url = f"/api/images/phonon/{filename}"
                    logger.warning(f"⚠️ Could not extract session_id from path, using filename only: {csv_url}")

                file_metadata['phonon_dos_csv_url'] = csv_url
                file_metadata['phonon_dos_csv_path'] = csv_path

                # 🔧 优化：不传输完整 CSV 内容，只传递下载 URL
                # 前端可以通过 URL 按需下载 CSV 文件
                # inline_csv = DataProcessor._read_text_file(csv_path)
                # if inline_csv is not None:
                #     file_metadata['phonon_dos_csv_content'] = inline_csv

                logger.info(f"📄 Found phonon DOS CSV: {csv_url}")

                # 🔧 同时发送为独立的文件数据，确保在右侧面板显示
                await DataProcessor._send_message(websocket, "file_data", {
                    "files": [{
                        "id": f"phonon_dos_{filename}",
                        "type": "csv",
                        "name": f"声子态密度数据 - {filename}",
                        "downloadUrl": csv_url,
                        "filePath": csv_path,
                        "createdAt": datetime.now().timestamp() * 1000,
                        "extra": {
                            "category": "phonon_dos"
                        }
                    }],
                    "agentId": agent_id,
                    "sessionId": session_id,
                    "timestamp": datetime.now().isoformat()
                })

            # If we found any file links, send them as metadata
            if file_metadata:
                logger.info(f"📄 Sending file metadata: {file_metadata}")

                # Send file metadata as part of the message metadata
                # This will be picked up by the frontend and displayed in the message
                await DataProcessor._send_message(websocket, "file_metadata", {
                    "agentId": agent_id,
                    "sessionId": session_id,
                    "metadata": file_metadata,
                    "timestamp": datetime.now().isoformat()
                })

                logger.info(f"✅ Sent file metadata to frontend (session: {session_id})")
                return True
            else:
                logger.debug("No file links found in tool result")
                return False

        except Exception as e:
            logger.error(f"Failed to process file links: {e}")
            return False

    @staticmethod
    def _get_database_name(data: Dict[str, Any]) -> str:
        """Extract database name from tool result"""
        # Try to get from structures first
        structures = data.get("structures", [])
        if structures and len(structures) > 0:
            first_structure = structures[0]
            if isinstance(first_structure, dict):
                source = first_structure.get("source", {})
                if isinstance(source, dict):
                    db_name = source.get("database")
                    if db_name:
                        return db_name

        # Fallback to other fields
        return (
            data.get("database") or
            data.get("query_info", {}).get("database") or
            data.get("source", {}).get("database") or
            "Unknown"
        )
    
    @staticmethod
    async def _send_message(websocket: Any, message_type: str, data: Dict[str, Any]):
        """Send message through WebSocket"""
        import json

        # 检查WebSocket连接状态
        if not websocket or websocket.closed:
            logger.warning(f"⚠️ WebSocket is closed, cannot send {message_type} message")
            return

        try:
            message = {
                "type": message_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }

            await websocket.send(json.dumps(message))
            logger.debug(f"📤 [WebSocket] Sent {message_type}, data size: {len(json.dumps(data))} bytes")
        except Exception as e:
            logger.warning(f"⚠️ Failed to send {message_type} message: {e}")

    @staticmethod
    def _read_text_file(file_path: str, max_bytes: int = 512_000) -> Optional[str]:
        """
        Read small text files so that CSV/Markdown content can be inlined.

        Args:
            file_path: File path relative to project root or absolute
            max_bytes: Safety limit to avoid shipping large payloads over WebSocket
        """
        try:
            if not file_path:
                return None

            raw_path = Path(file_path)
            candidate_paths = []

            if raw_path.is_absolute():
                candidate_paths.append(raw_path)
            else:
                candidate_paths.append((Path.cwd() / raw_path).resolve())
                candidate_paths.append((Path.cwd() / "mcp_servers" / raw_path).resolve())
                candidate_paths.append((Path(__file__).resolve().parent.parent.parent / raw_path).resolve())

            path = next((p for p in candidate_paths if p.exists() and p.is_file()), None)
            if path is None:
                logger.warning(f"📄 Inline file not found: {file_path} -> tried {candidate_paths}")
                return None

            size = path.stat().st_size
            if size > max_bytes:
                logger.info(
                    "📄 Skipping inline content because file is too large",
                    extra={"file": str(path), "size": size, "limit": max_bytes}
                )
                return None

            return path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"📄 Failed to read inline file {file_path}: {e}")
            return None

    @staticmethod
    def validate_structure_data(structure: Dict[str, Any]) -> bool:
        """
        Validate structure data has required fields
        
        Args:
            structure: Structure data dict
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["id", "formula", "spaceGroup", "latticeParameters", "atoms"]
        
        for field in required_fields:
            if field not in structure:
                logger.warning(f"⚠️ Structure missing required field: {field}")
                return False
        
        # Validate latticeParameters
        if not isinstance(structure["latticeParameters"], dict):
            logger.warning("⚠️ latticeParameters is not a dict")
            return False
        
        lattice_fields = ["a", "b", "c", "alpha", "beta", "gamma"]
        for field in lattice_fields:
            if field not in structure["latticeParameters"]:
                logger.warning(f"⚠️ latticeParameters missing field: {field}")
                return False
        
        # Validate atoms
        if not isinstance(structure["atoms"], list) or len(structure["atoms"]) == 0:
            logger.warning("⚠️ atoms is not a non-empty list")
            return False
        
        return True
    
    @staticmethod
    def validate_image_data(image: Dict[str, Any]) -> bool:
        """
        Validate image data has required fields
        
        Args:
            image: Image data dict
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["name", "type", "url"]
        
        for field in required_fields:
            if field not in image:
                logger.warning(f"⚠️ Image missing required field: {field}")
                return False
        
        return True
    
    @staticmethod
    async def process_uploaded_structure(
        structure_data: Dict[str, Any],
        websocket: Any,
        agent_id: str = "upload"
    ) -> bool:
        """
        Process user-uploaded structure
        
        Args:
            structure_data: Uploaded structure data
            websocket: WebSocket connection
            agent_id: Agent ID (default: "upload")
            
        Returns:
            True if processed successfully
        """
        try:
            # Mark as uploaded
            structure = StructureConverter.mark_as_uploaded(structure_data)
            
            # Validate
            if not DataProcessor.validate_structure_data(structure):
                logger.error("❌ Uploaded structure failed validation")
                return False
            
            # Send to frontend
            await DataProcessor._send_message(websocket, "structure_data", {
                "structures": [structure],
                "agentId": agent_id,
                "timestamp": datetime.now().isoformat(),
                "source": "Upload"
            })
            
            logger.info("✅ Processed uploaded structure")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process uploaded structure: {e}")
            return False

