"""
Static File Service

Serves static files like phonon spectra images, generated structures, etc.
"""

import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import server_config
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


def get_api_base_url() -> str:
    """Get API base URL from environment variable"""
    return os.getenv('VITE_API_URL', f'http://{server_config.HTTP_HOST}:{server_config.HTTP_PORT}')


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

        # Phonon results directory - mount first (most specific)
        phonon_dir = server_config.PHONON_RESULTS_DIR
        if os.path.exists(phonon_dir):
            app.mount(
                "/api/images/phonon_results",
                StaticFiles(directory=phonon_dir),
                name="phonon_images"
            )
            logger.info(f"✅ Static files: /api/images/phonon_results -> {phonon_dir}")
        else:
            logger.warning(f"⚠️ Phonon results directory not found: {phonon_dir}")

        # Generated structures directory - mount second (specific)
        structures_dir = server_config.GENERATED_STRUCTURES_DIR
        if os.path.exists(structures_dir):
            app.mount(
                "/api/images/generated_structures",
                StaticFiles(directory=structures_dir),
                name="structure_images"
            )
            logger.info(f"✅ Static files: /api/images/generated_structures -> {structures_dir}")
        else:
            logger.warning(f"⚠️ Generated structures directory not found: {structures_dir}")

        # Session images directory (会话隔离的图片) - mount last (least specific, catch-all)
        session_images_dir = SessionManager.IMAGES_DIR
        if session_images_dir.exists():
            app.mount(
                "/api/images",
                StaticFiles(directory=str(session_images_dir)),
                name="session_images"
            )
            logger.info(f"✅ Static files: /api/images -> {session_images_dir}")
        else:
            # Fallback to general images directory
            mcp_servers_dir = os.path.join(server_config.STATIC_FILES_ROOT, "mcp_servers")
            if os.path.exists(mcp_servers_dir):
                app.mount(
                    "/api/images",
                    StaticFiles(directory=mcp_servers_dir),
                    name="all_images"
                )
                logger.info(f"✅ Static files: /api/images -> {mcp_servers_dir}")
    
    @staticmethod
    def get_file_url(filename: str, file_type: str = "phonon_results") -> str:
        """
        Get URL for a static file
        
        Args:
            filename: File name
            file_type: Type of file (phonon_results, generated_structures, etc.)
            
        Returns:
            Full URL to access the file
        """
        return f"http://{server_config.HTTP_HOST}:{server_config.HTTP_PORT}/api/images/{file_type}/{filename}"
    
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
                        'url': f"{get_api_base_url()}/api/images/phonon_results/{url_path}",
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
                'url': f"{get_api_base_url()}/api/images/phonon_results/{url_path}",
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
                'url': f"{get_api_base_url()}/api/images/phonon_results/{url_path}",
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

