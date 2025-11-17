"""
Image Data Handler

Handles image data from MCP tools, including phonon spectra, band structures, etc.
Generates proper URLs for frontend access.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from urllib.parse import urlparse

from .config import server_config

logger = logging.getLogger(__name__)


class ImageHandler:
    """Handle image data and URL generation"""

    _vite_api_url = os.getenv("VITE_API_URL")

    @staticmethod
    def _build_origin(default_host: Optional[str] = None, default_port: Optional[int] = None) -> str:
        host = os.getenv("RESEARCHMIND_HTTP_HOST", default_host or server_config.HTTP_HOST)
        port = os.getenv("RESEARCHMIND_HTTP_PORT", str(default_port) if default_port is not None else "50002")
        if host == "0.0.0.0":
            host = "127.0.0.1"
        return f"http://{host}:{port}"

    if _vite_api_url:
        _candidate = _vite_api_url.strip()
        parsed = urlparse(_candidate)
        if not _candidate.startswith('/') and parsed.scheme and parsed.netloc:
            BASE_URL = f"{parsed.scheme}://{parsed.netloc}"
        else:
            BASE_URL = _build_origin()
    else:
        BASE_URL = _build_origin()

    @staticmethod
    def set_base_url(host: str, port: int):
        """Set base URL for image access"""
        vite_api_url = os.getenv("VITE_API_URL")
        if vite_api_url:
            candidate = vite_api_url.strip()
            parsed = urlparse(candidate)
            if not candidate.startswith('/') and parsed.scheme and parsed.netloc:
                ImageHandler.BASE_URL = f"{parsed.scheme}://{parsed.netloc}"
                return

        ImageHandler.BASE_URL = ImageHandler._build_origin(host, port)

    @staticmethod
    def extract_images_from_tool_result(result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract image data from MCP tool result

        Handles:
        - Direct images field
        - Phonon band plot paths
        - Phonon DOS plot paths
        - Other plot paths

        Args:
            result: Tool result data

        Returns:
            List of image dicts with proper URLs
        """
        images = []

        try:
            logger.info(f"🔍 Extracting images from tool result")
            logger.info(f"🔍 Result type: {type(result)}")
            logger.info(f"🔍 Result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")

            # Method 1: Direct images field (preferred - MCP tools already provide formatted images)
            if "images" in result and isinstance(result["images"], list):
                logger.info(f"✅ Found {len(result['images'])} images in images field")
                for i, img in enumerate(result["images"]):
                    logger.info(f"🔍 Image {i+1} keys: {list(img.keys())}")
                    logger.info(f"🔍 Image {i+1} 'available': {img.get('available', 'NOT_SET')}")
                images.extend(result["images"])

            # Method 2-3: Only extract from paths if no images field exists
            elif result.get("phonon_band_plot_path") or result.get("phonon_dos_plot_path"):
                # 🆕 提取 CSV 路径（用于原始数据展示）
                dispersion_csv = result.get("phonon_dispersion_csv")
                dos_csv = result.get("phonon_dos_csv")

                # Method 2: Phonon band plot
                if result.get("phonon_band_plot_path"):
                    logger.info(f"🔍 Found phonon_band_plot_path: {result['phonon_band_plot_path']}")
                    logger.info(f"🔍 phonon_band_plot_available: {result.get('phonon_band_plot_available')}")

                    if result.get("phonon_band_plot_available"):
                        image = ImageHandler._create_phonon_image(
                            result["phonon_band_plot_path"],
                            "phonon_dispersion",
                            "Phonon Dispersion",
                            dispersion_csv=dispersion_csv,
                            dos_csv=dos_csv
                        )
                        if image:
                            images.append(image)
                            logger.info(f"✅ Added phonon band image: {image['url']}")

                # Method 3: Phonon DOS plot
                if result.get("phonon_dos_plot_path"):
                    logger.info(f"🔍 Found phonon_dos_plot_path: {result['phonon_dos_plot_path']}")
                    logger.info(f"🔍 phonon_dos_plot_available: {result.get('phonon_dos_plot_available')}")

                    if result.get("phonon_dos_plot_available"):
                        image = ImageHandler._create_phonon_image(
                            result["phonon_dos_plot_path"],
                            "phonon_dos",
                            "Phonon DOS",
                            dispersion_csv=dispersion_csv,
                            dos_csv=dos_csv
                        )
                        if image:
                            images.append(image)
                            logger.info(f"✅ Added phonon DOS image: {image['url']}")
            
            # Method 4: Generic plot paths
            for key in ["band_structure_path", "dos_path", "plot_path"]:
                if key in result and result[key]:
                    image = ImageHandler._create_generic_image(
                        result[key],
                        key.replace("_path", ""),
                        result.get(f"{key}_name", key)
                    )
                    if image:
                        images.append(image)
            
            logger.info(f"📊 Total images extracted: {len(images)}")
            
        except Exception as e:
            logger.error(f"Failed to extract images from tool result: {e}")
        
        return images
    
    @staticmethod
    def _create_phonon_image(path: str, image_type: str, name: str,
                            dispersion_csv: Optional[str] = None,
                            dos_csv: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create phonon image data with proper URL and CSV paths"""
        try:
            # Extract filename from path
            filename = Path(path).name

            # 🔧 修复：从路径中提取 session_id 和相对路径
            # 路径格式: session_data/simulation/{session_id}/phonon_results/file.png
            # URL 格式: /api/images/phonon/{session_id}/phonon_results/file.png
            normalized_path = path.replace('\\', '/')

            # 尝试从路径中提取 session_id 和相对路径
            if 'session_data/simulation/' in normalized_path:
                # 提取 session_data/simulation/ 后面的部分
                relative_part = normalized_path.split('session_data/simulation/', 1)[1]
                # relative_part 格式: {session_id}/phonon_results/file.png
                url = f"/api/images/phonon/{relative_part}"
                logger.info(f"🔗 Generated phonon URL from session_data path: {url}")
            elif '/simulation/' in normalized_path:
                # 旧路径格式兼容
                relative_part = normalized_path.split('/simulation/', 1)[1]
                url = f"/api/images/phonon/{relative_part}"
                logger.info(f"🔗 Generated phonon URL from simulation path: {url}")
            else:
                # 后备方案：只使用文件名（可能不工作，但至少不会崩溃）
                url = f"/api/images/phonon/{filename}"
                logger.warning(f"⚠️ Could not extract session_id from path, using filename only: {url}")

            # Check if file exists
            available = os.path.exists(path)
            if not available:
                logger.warning(f"⚠️ Image file not found: {path}")

            image_data = {
                "name": name,
                "type": image_type,
                "path": path,
                "url": url,
                "filename": filename,
                "available": available,
                "timestamp": datetime.now().isoformat()
            }

            # 🆕 添加 CSV 数据路径（如果提供）
            if dispersion_csv:
                logger.info(f"🔍 Processing dispersion CSV: {dispersion_csv}")
                # 同样从 CSV 路径中提取相对路径
                csv_normalized = dispersion_csv.replace('\\', '/')
                logger.info(f"🔍 Normalized CSV path: {csv_normalized}")
                if 'session_data/simulation/' in csv_normalized:
                    csv_relative = csv_normalized.split('session_data/simulation/', 1)[1]
                    csv_url = f"/api/images/phonon/{csv_relative}"
                    logger.info(f"✅ Extracted from session_data/simulation/: {csv_url}")
                elif '/simulation/' in csv_normalized:
                    csv_relative = csv_normalized.split('/simulation/', 1)[1]
                    csv_url = f"/api/images/phonon/{csv_relative}"
                    logger.info(f"✅ Extracted from /simulation/: {csv_url}")
                else:
                    csv_filename = Path(dispersion_csv).name
                    csv_url = f"/api/images/phonon/{csv_filename}"
                    logger.warning(f"⚠️ Using filename only: {csv_url}")

                image_data["dispersionCsvPath"] = csv_url
                logger.info(f"📊 Added dispersion CSV path: {csv_url}")

            if dos_csv:
                logger.info(f"🔍 Processing DOS CSV: {dos_csv}")
                # 同样从 CSV 路径中提取相对路径
                csv_normalized = dos_csv.replace('\\', '/')
                logger.info(f"🔍 Normalized CSV path: {csv_normalized}")
                if 'session_data/simulation/' in csv_normalized:
                    csv_relative = csv_normalized.split('session_data/simulation/', 1)[1]
                    csv_url = f"/api/images/phonon/{csv_relative}"
                    logger.info(f"✅ Extracted from session_data/simulation/: {csv_url}")
                elif '/simulation/' in csv_normalized:
                    csv_relative = csv_normalized.split('/simulation/', 1)[1]
                    csv_url = f"/api/images/phonon/{csv_relative}"
                    logger.info(f"✅ Extracted from /simulation/: {csv_url}")
                else:
                    csv_filename = Path(dos_csv).name
                    csv_url = f"/api/images/phonon/{csv_filename}"
                    logger.warning(f"⚠️ Using filename only: {csv_url}")

                image_data["dosCsvPath"] = csv_url
                logger.info(f"📊 Added DOS CSV path: {csv_url}")

            return image_data
        except Exception as e:
            logger.error(f"Failed to create phonon image data: {e}")
            return None
    
    @staticmethod
    def _create_generic_image(path: str, image_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Create generic image data with proper URL"""
        try:
            filename = Path(path).name

            # Determine URL prefix based on path（不包含 /api 前缀）
            if "phonon" in path.lower():
                url_prefix = "/images/phonon"
            elif "structure" in path.lower() or "generated" in path.lower():
                url_prefix = "/images/generated_structures"
            else:
                url_prefix = "/images"

            # 统一使用 /images/... 格式（不包含 /api 前缀）
            # Nginx 代理会添加 /api 前缀，前端会自动转换为完整 URL
            url = f"{url_prefix}/{filename}"

            return {
                "name": name,
                "type": image_type,
                "path": path,
                "url": url,
                "filename": filename,
                "available": True,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to create generic image data: {e}")
            return None
    
    @staticmethod
    def verify_image_exists(image: Dict[str, Any]) -> bool:
        """Verify that image file exists on disk"""
        try:
            if "path" in image:
                return os.path.exists(image["path"])
            return False
        except Exception as e:
            logger.warning(f"Failed to verify image existence: {e}")
            return False
    
    @staticmethod
    def get_image_url(filename: str, image_type: str = "phonon") -> str:
        """
        Generate image URL for a given filename

        Args:
            filename: Image filename
            image_type: Type of image (phonon, generated_structures, etc.)

        Returns:
            Full URL to access the image (relative path)
        """
        # 统一使用 /images/... 格式（不包含 /api 前缀）
        # Nginx 代理会添加 /api 前缀，前端会自动转换为完整 URL
        return f"/images/{image_type}/{filename}"
    
    @staticmethod
    def standardize_image_data(image: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize image data format

        Ensures all images have:
        - name
        - type
        - url
        - available flag
        - timestamp

        Args:
            image: Raw image data

        Returns:
            Standardized image data
        """
        try:
            logger.info(f"🔍 Standardizing image data: {image.get('name', 'Unknown')}")
            logger.info(f"🔍 Input image keys: {list(image.keys())}")
            logger.info(f"🔍 Input 'available' value: {image.get('available', 'NOT_SET')}")
            logger.info(f"🔍 Input 'available' in image: {'available' in image}")

            standardized = image.copy()

            logger.info(f"🔍 After copy, 'available' in standardized: {'available' in standardized}")
            logger.info(f"🔍 After copy, 'available' value: {standardized.get('available', 'NOT_SET')}")

            # Ensure required fields
            if "name" not in standardized:
                standardized["name"] = standardized.get("filename", "Unknown")

            if "type" not in standardized:
                standardized["type"] = "generic"

            if "url" not in standardized and "path" in standardized:
                # Try to generate URL from path
                filename = Path(standardized["path"]).name
                standardized["url"] = ImageHandler.get_image_url(filename)

            # Only verify file existence if available flag is not already set
            if "available" not in standardized:
                logger.info(f"⚠️ 'available' NOT in standardized, verifying file existence")
                standardized["available"] = ImageHandler.verify_image_exists(standardized)
                logger.info(f"🔍 Verified image existence: {standardized['name']} -> {standardized['available']}")
            else:
                logger.info(f"✅ Using pre-set available flag for {standardized['name']}: {standardized['available']}")

            if "timestamp" not in standardized:
                standardized["timestamp"] = datetime.now().isoformat()

            logger.info(f"✅ Standardized image: {standardized['name']}, available={standardized.get('available')}")

            return standardized

        except Exception as e:
            logger.error(f"Failed to standardize image data: {e}", exc_info=True)
            return image
    
    @staticmethod
    def create_image_list_response(images: List[Dict[str, Any]], agent_id: str) -> Dict[str, Any]:
        """
        Create a standardized image list response for WebSocket
        
        Args:
            images: List of image dicts
            agent_id: Agent ID that generated the images
            
        Returns:
            Response dict ready for WebSocket transmission
        """
        # Standardize all images
        standardized_images = [ImageHandler.standardize_image_data(img) for img in images]
        
        # Filter out unavailable images
        available_images = [img for img in standardized_images if img.get("available", False)]

        if len(available_images) < len(standardized_images):
            unavailable_count = len(standardized_images) - len(available_images)
            logger.warning(f"⚠️ {unavailable_count} image{'s' if unavailable_count > 1 else ''} {'are' if unavailable_count > 1 else 'is'} not available")
        
        return {
            "images": available_images,
            "agentId": agent_id,
            "timestamp": datetime.now().isoformat(),
            "total": len(available_images)
        }

