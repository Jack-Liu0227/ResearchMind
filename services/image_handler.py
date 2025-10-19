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

from .config import server_config

logger = logging.getLogger(__name__)


class ImageHandler:
    """Handle image data and URL generation"""

    # Base URL for static files (will be set by server)
    # 优先使用 VITE_API_URL（前端调用的API地址）
    _vite_api_url = os.getenv("VITE_API_URL")
    if _vite_api_url:
        BASE_URL = _vite_api_url
    else:
        _default_host = os.getenv("RESEARCHMIND_HTTP_HOST", server_config.HTTP_HOST)
        _default_port = os.getenv("RESEARCHMIND_HTTP_PORT", "50006")
        if _default_host == "0.0.0.0":
            _default_host = "127.0.0.1"
        BASE_URL = f"http://{_default_host}:{_default_port}"

    @staticmethod
    def set_base_url(host: str, port: int):
        """Set base URL for image access"""
        # 优先使用 VITE_API_URL（前端调用的API地址）
        vite_api_url = os.getenv("VITE_API_URL")
        if vite_api_url:
            ImageHandler.BASE_URL = vite_api_url
        else:
            http_host = os.getenv("RESEARCHMIND_HTTP_HOST", host)
            http_port = os.getenv("RESEARCHMIND_HTTP_PORT", str(port))
            if http_host == "0.0.0.0":
                http_host = "127.0.0.1"
            ImageHandler.BASE_URL = f"http://{http_host}:{http_port}"
    
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
                # Method 2: Phonon band plot
                if result.get("phonon_band_plot_path"):
                    logger.info(f"🔍 Found phonon_band_plot_path: {result['phonon_band_plot_path']}")
                    logger.info(f"🔍 phonon_band_plot_available: {result.get('phonon_band_plot_available')}")

                    if result.get("phonon_band_plot_available"):
                        image = ImageHandler._create_phonon_image(
                            result["phonon_band_plot_path"],
                            "phonon_dispersion",
                            "Phonon Dispersion"
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
                            "Phonon DOS"
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
    def _create_phonon_image(path: str, image_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Create phonon image data with proper URL"""
        try:
            # Extract filename from path
            filename = Path(path).name

            # Generate URL - 统一使用 /images/... 格式（不包含 /api 前缀）
            # Nginx 代理会添加 /api 前缀，前端会自动转换为完整 URL
            url = f"/images/phonon_results/{filename}"

            # Check if file exists
            available = os.path.exists(path)
            if not available:
                logger.warning(f"⚠️ Image file not found: {path}")

            return {
                "name": name,
                "type": image_type,
                "path": path,
                "url": url,
                "filename": filename,
                "available": available,
                "timestamp": datetime.now().isoformat()
            }
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
                url_prefix = "/images/phonon_results"
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
    def get_image_url(filename: str, image_type: str = "phonon_results") -> str:
        """
        Generate image URL for a given filename

        Args:
            filename: Image filename
            image_type: Type of image (phonon_results, generated_structures, etc.)

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

