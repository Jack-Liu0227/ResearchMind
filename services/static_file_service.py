"""
Static File Service

Serves static files like phonon spectra images, generated structures, etc.
"""

import os
import logging
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import server_config
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


def get_api_base_url() -> str:
    """Get API base origin from environment variable or construct from config"""
    api_url = os.getenv('VITE_API_URL')

    default_origin_host = os.getenv('RESEARCHMIND_HTTP_HOST') or server_config.HTTP_HOST
    default_origin_port = os.getenv('RESEARCHMIND_HTTP_PORT', '50002')

    if default_origin_host == '0.0.0.0':
        default_origin_host = '127.0.0.1'

    default_origin = f'http://{default_origin_host}:{default_origin_port}'

    if not api_url:
        return default_origin

    api_url = api_url.strip()
    if api_url.startswith('/'):
        return default_origin

    parsed = urlparse(api_url)
    if parsed.scheme and parsed.netloc:
        return f'{parsed.scheme}://{parsed.netloc}'

    return default_origin



class StaticFileService:
    """Static file service for images and other files"""
    
    @staticmethod
    def setup_static_files(app: FastAPI):
        """
        Setup static file routes on FastAPI app

        Args:
            app: FastAPI application instance
        """
        # Setup CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=server_config.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # IMPORTANT: Mount more specific paths BEFORE less specific ones
        # FastAPI matches routes in the order they are mounted
        # More specific paths must be mounted first to avoid being shadowed

        # Papers download directory - mount first (most specific)
        # 🔧 使用统一的 session_data 目录
        # 这是论文搜索结果的 CSV 和 MD 文件存储位置
        # 注意：挂载点是 /api/download，目录是 session_data
        # 这样 /api/download/papers/{session_id}/file.csv 会映射到 session_data/papers/{session_id}/file.csv
        paper_search_dir = os.path.abspath(server_config.SESSION_DATA_DIR)
        # 🔧 确保目录存在，如果不存在则创建
        if not os.path.exists(paper_search_dir):
            os.makedirs(paper_search_dir, exist_ok=True)
            logger.info(f"📁 Created session data directory: {paper_search_dir}")

        app.mount(
            "/api/download",
            StaticFiles(directory=paper_search_dir, check_dir=False),
            name="papers_download"
        )
        # Legacy path support without /api prefix
        app.mount(
            "/download",
            StaticFiles(directory=paper_search_dir, check_dir=False),
            name="papers_download_legacy"
        )
        logger.info(f"✅ Static files: /api/download -> {paper_search_dir}")
        logger.info(f"✅ Static files: /download -> {paper_search_dir}")

        # 🔧 使用统一的 session_data 目录结构
        # Phonon results directory - mount second (specific)
        # 声子谱图片和 CSV 文件 - 使用 session_data/simulation/*/phonon_results
        # 注意：/api/images/phonon/{session_id}/file.csv 会映射到 session_data/simulation/{session_id}/phonon_results/file.csv
        phonon_dir = os.path.abspath(os.path.join(server_config.SESSION_DATA_DIR, "simulation"))
        # 🔧 确保目录存在，如果不存在则创建
        if not os.path.exists(phonon_dir):
            os.makedirs(phonon_dir, exist_ok=True)
            logger.info(f"📁 Created simulation directory: {phonon_dir}")

        app.mount(
            "/api/images/phonon",
            StaticFiles(directory=phonon_dir, check_dir=False),
            name="phonon_images"
        )
        logger.info(f"✅ Static files: /api/images/phonon -> {phonon_dir}")

        # 🆕 Thermal conductivity results directory - mount for CSV files
        # 使用 session_data/simulation/*/thermal_conductivity
        # 注意：/api/files/thermal_conductivity/{session_id}/file.csv 会映射到 session_data/simulation/{session_id}/thermal_conductivity/file.csv
        thermal_conductivity_dir = os.path.abspath(os.path.join(server_config.SESSION_DATA_DIR, "simulation"))
        # 🔧 确保目录存在，如果不存在则创建
        if not os.path.exists(thermal_conductivity_dir):
            os.makedirs(thermal_conductivity_dir, exist_ok=True)
            logger.info(f"📁 Created simulation directory: {thermal_conductivity_dir}")

        app.mount(
            "/api/files/thermal_conductivity",
            StaticFiles(directory=thermal_conductivity_dir, check_dir=False),
            name="thermal_conductivity_files"
        )
        logger.info(f"✅ Static files: /api/files/thermal_conductivity -> {thermal_conductivity_dir}")

        # Generated structures directory - mount third (specific)
        # 🔧 CrystalLM 生成的结构 - 使用 session_data/simulation/*/generated
        # 注意：/api/images/generated_structures/{session_id}/file.cif 会映射到 session_data/simulation/{session_id}/generated/file.cif
        structures_dir = os.path.abspath(server_config.GENERATED_STRUCTURES_DIR)
        # 🔧 确保目录存在，如果不存在则创建
        if not os.path.exists(structures_dir):
            os.makedirs(structures_dir, exist_ok=True)
            logger.info(f"📁 Created generated structures directory: {structures_dir}")

        app.mount(
            "/api/images/generated_structures",
            StaticFiles(directory=structures_dir, check_dir=False),
            name="structure_images"
        )
        logger.info(f"✅ Static files: /api/images/generated_structures -> {structures_dir}")

        # Note: /api/structures/relaxed mount removed (directory never existed)
        # All relaxed structures now use session-isolated paths: /api/structures/{session_id}/relax/

        # 🔧 Simulation CIF structures directory (会话隔离的弛豫结构文件)
        # 使用 session_data/simulation/*/cif
        simulation_cif_dir = os.path.abspath(os.path.join(server_config.SESSION_DATA_DIR, "simulation"))
        # 🔧 确保目录存在，如果不存在则创建
        if not os.path.exists(simulation_cif_dir):
            os.makedirs(simulation_cif_dir, exist_ok=True)
            logger.info(f"📁 Created simulation CIF directory: {simulation_cif_dir}")

        app.mount(
            "/api/structures",
            StaticFiles(directory=simulation_cif_dir, check_dir=False),
            name="simulation_structures"
        )
        logger.info(f"✅ Static files: /api/structures -> {simulation_cif_dir}")

        # 🔧 优化：删除冗余的会话结构和图片挂载
        # 原因：
        # 1. session_data/structures 已被 /api/structures 替代
        # 2. session_data/images 从未被实际使用，且会覆盖 /api/images/* 子路径
        # 3. 所有图片都保存在具体的目录（如 phonon_results, generated_structures）

        # 如果未来需要会话隔离的图片，应使用不同的路径（如 /api/session/images）
        # 而不是使用 /api/images 这种会覆盖子路径的通用路径
    
    @staticmethod
    def get_file_url(filename: str, file_type: str = "phonon_results") -> str:
        """
        Get URL for a static file

        Args:
            filename: File name
            file_type: Type of file (phonon_results, generated_structures, etc.)

        Returns:
            Full URL to access the file (relative path)
        """
        # 统一使用 /images/... 格式（不包含 /api 前缀）
        # Nginx 代理会添加 /api 前缀，前端会自动转换为完整 URL
        return f"/images/{file_type}/{filename}"
    
    @staticmethod
    def verify_file_exists(filepath: str) -> bool:
        """
        Verify that a file exists
        
        Args:
            filepath: Path to file
            
        Returns:
            True if file exists
        """
        return os.path.exists(filepath) and os.path.isfile(filepath)
    
    @staticmethod
    def list_phonon_results() -> list:
        """
        List all phonon result files (including subdirectories)

        Returns:
            List of dicts with file info: {name, url, path, type}
        """
        phonon_dir = server_config.PHONON_RESULTS_DIR
        if not os.path.exists(phonon_dir):
            return []

        files = []
        # Walk through directory and subdirectories
        for root, dirs, filenames in os.walk(phonon_dir):
            for filename in filenames:
                if filename.endswith(('.png', '.jpg', '.jpeg', '.svg')):
                    # Get relative path from phonon_dir
                    rel_path = os.path.relpath(os.path.join(root, filename), phonon_dir)
                    # Replace backslashes with forward slashes for URLs
                    url_path = rel_path.replace('\\', '/')

                    # Determine type from filename
                    file_type = 'phonon_dispersion' if 'band' in filename.lower() else 'phonon_dos'

                    files.append({
                        'name': filename,
                        'url': f"/api/images/phonon/{url_path}",
                        'path': url_path,
                        'type': file_type,
                        'description': f"声子谱图像: {filename}"
                    })

        return sorted(files, key=lambda x: x['name'], reverse=True)  # Most recent first
    
    @staticmethod
    def list_phonon_examples() -> list:
        """
        List phonon example files from the examples subdirectory
        Returns only one band and one dos example (the most recent ones)

        Returns:
            List of dicts with file info: {name, url, path, type}
        """
        examples_dir = os.path.join(server_config.PHONON_RESULTS_DIR, "examples")

        logger.info(f"🔍 Looking for phonon examples in: {examples_dir}")
        logger.info(f"🔍 Directory exists: {os.path.exists(examples_dir)}")

        if not os.path.exists(examples_dir):
            logger.warning(f"⚠️ Examples directory not found: {examples_dir}")
            logger.info(f"💡 Please create the directory and add example images")
            return []

        band_files = []
        dos_files = []

        # Separate band and dos files from the examples directory
        try:
            for filename in os.listdir(examples_dir):
                if filename.endswith(('.png', '.jpg', '.jpeg', '.svg')):
                    if 'band' in filename.lower():
                        band_files.append(filename)
                        logger.info(f"🔍 Found band file: {filename}")
                    elif 'dos' in filename.lower():
                        dos_files.append(filename)
                        logger.info(f"🔍 Found dos file: {filename}")
        except Exception as e:
            logger.error(f"❌ Error listing examples directory: {e}")
            return []

        # Sort by filename (most recent first based on timestamp in filename)
        band_files.sort(reverse=True)
        dos_files.sort(reverse=True)

        # Take only the most recent one of each type
        result = []

        if band_files:
            filename = band_files[0]
            url_path = f"examples/{filename}"
            result.append({
                'name': filename,
                'url': f"{get_api_base_url()}/api/images/phonon/{url_path}",
                'path': url_path,
                'type': 'phonon_dispersion',
                'description': f"示例声子色散关系图"
            })
            logger.info(f"✅ Selected band example: {filename}")

        if dos_files:
            filename = dos_files[0]
            url_path = f"examples/{filename}"
            result.append({
                'name': filename,
                'url': f"{get_api_base_url()}/api/images/phonon/{url_path}",
                'path': url_path,
                'type': 'phonon_dos',
                'description': f"示例声子态密度图"
            })
            logger.info(f"✅ Selected dos example: {filename}")

        logger.info(f"📊 Returning {len(result)} example images: {[f['name'] for f in result]}")
        return result

    @staticmethod
    def list_generated_structures() -> list:
        """
        List all generated structure files

        Returns:
            List of generated structure filenames
        """
        structures_dir = server_config.GENERATED_STRUCTURES_DIR
        if not os.path.exists(structures_dir):
            return []

        files = []
        for root, dirs, filenames in os.walk(structures_dir):
            for filename in filenames:
                if filename.endswith('.cif'):
                    rel_path = os.path.relpath(os.path.join(root, filename), structures_dir)
                    files.append(rel_path)

        return sorted(files, reverse=True)  # Most recent first

