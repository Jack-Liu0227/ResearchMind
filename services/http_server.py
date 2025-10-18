"""
HTTP API Server

Provides HTTP API endpoints for structure conversion, health checks, etc.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import os

from .config import server_config
from .static_file_service import StaticFileService
from .structure_converter import StructureConverter

logger = logging.getLogger(__name__)

# Try to import pymatgen
try:
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.io.cif import CifParser
    PYMATGEN_AVAILABLE = True
    logger.info("✅ pymatgen available")
except ImportError:
    PYMATGEN_AVAILABLE = False
    logger.warning("⚠️ pymatgen not available, CIF conversion disabled")


# Pydantic models for API
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    pymatgen_available: bool
    agents_available: bool


class CIFConversionRequest(BaseModel):
    cif_content: str
    to_conventional: bool = True


class StructureResponse(BaseModel):
    formula: str
    spaceGroup: str
    latticeParameters: Dict[str, float]
    atoms: list
    properties: Optional[Dict[str, Any]] = None


class UploadResponse(BaseModel):
    success: bool
    message: str
    structures: list
    count: int


class ServiceStatusResponse(BaseModel):
    websocket_server: Dict[str, Any]
    http_server: Dict[str, Any]
    mcp_servers: Dict[str, Any]
    timestamp: str


class HTTPServer:
    """HTTP API server for ResearchMind"""
    
    def __init__(self):
        """Initialize HTTP server"""
        self.app = FastAPI(
            title="ResearchMind API",
            description="HTTP API for ResearchMind crystal structure analysis",
            version="1.0.0"
        )
        
        # Configuration constants
        self.MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
        self.MAX_FILES_COUNT = 50  # Maximum number of files in batch upload
        
        # Setup routes
        self._setup_routes()

        # Setup upload endpoints
        self._setup_upload_endpoints()

        # Setup static files
        StaticFileService.setup_static_files(self.app)
    
    def _setup_routes(self):
        """Setup API routes"""

        @self.app.get("/api/debug/cif-validation")
        async def debug_cif_validation():
            """Debug endpoint to check CIF validation"""
            return {
                "status": "ok",
                "message": "CIF validation endpoint is working",
                "pymatgen_available": PYMATGEN_AVAILABLE,
                "nginx_buffering": "disabled (proxy_request_buffering off)",
                "max_file_size": f"{self.MAX_FILE_SIZE // (1024*1024)}MB"
            }

        @self.app.get("/")
        async def root():
            """API root endpoint"""
            return {
                "name": "ResearchMind API",
                "version": "1.0.0",
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "endpoints": {
                    "health": "/health",
                    "docs": "/docs",
                    "service_status": "/api/service_status",
                    "upload_structure": "/api/upload/structure",
                    "upload_structures": "/api/upload/structures",
                    "parse_cif": "/api/parse_cif",
                    "convert_to_conventional": "/api/convert_to_conventional",
                    "phonon_results": "/api/phonon_results",
                    "phonon_examples": "/api/phonon_examples",
                    "generated_structures": "/api/generated_structures",
                    "images": "/api/images/{type}/{filename}",
                    "download_file": "/api/download/{file_path:path}"
                }
            }
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint"""
            # Check if agents are available
            agents_available = False
            try:
                from agents.agent import research_coordinator
                agents_available = True
            except ImportError:
                pass

            return HealthResponse(
                status="healthy",
                timestamp=datetime.now().isoformat(),
                version="1.0.0",
                pymatgen_available=PYMATGEN_AVAILABLE,
                agents_available=agents_available
            )
        
        @self.app.get("/api/health", response_model=HealthResponse)
        async def api_health_check():
            """API Health check endpoint (alias for /health)"""
            return await health_check()
        
        @self.app.get("/api/service_status", response_model=ServiceStatusResponse)
        async def service_status():
            """Get service status"""
            from .config import mcp_config
            
            return ServiceStatusResponse(
                websocket_server={
                    "host": server_config.WEBSOCKET_HOST,
                    "port": server_config.WEBSOCKET_PORT,
                    "status": "running"
                },
                http_server={
                    "host": server_config.HTTP_HOST,
                    "port": server_config.HTTP_PORT,
                    "status": "running"
                },
                mcp_servers=mcp_config.SERVERS,
                timestamp=datetime.now().isoformat()
            )
        
        @self.app.get("/api/phonon_results")
        async def list_phonon_results():
            """List available phonon result files"""
            files = StaticFileService.list_phonon_results()
            return {
                "success": True,
                "phonon_results": files,  # 使用phonon_results字段,与前端期望一致
                "count": len(files),
                "timestamp": datetime.now().isoformat()
            }

        @self.app.get("/api/phonon_examples")
        async def list_phonon_examples():
            """List phonon example files from examples directory"""
            files = StaticFileService.list_phonon_examples()
            return {
                "success": True,
                "files": files,
                "count": len(files),
                "timestamp": datetime.now().isoformat()
            }

        @self.app.get("/api/generated_structures")
        async def list_generated_structures():
            """List available generated structure files"""
            files = StaticFileService.list_generated_structures()
            return {
                "files": files,
                "count": len(files),
                "timestamp": datetime.now().isoformat()
            }
        
        # Note: /api/images/{image_type}/{filename} is handled by StaticFiles middleware
        # Do NOT add an API route here as it will override the static file serving

        @self.app.post("/api/convert_to_conventional", response_model=StructureResponse)
        async def convert_to_conventional(request: CIFConversionRequest):
            """
            Convert crystal structure to conventional cell

            Workflow:
            1. Parse CIF file
            2. Symmetry analysis
            3. Convert to primitive cell
            4. Convert to conventional cell
            """
            if not PYMATGEN_AVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="pymatgen not available, CIF conversion disabled"
                )

            try:
                logger.info("📥 Received CIF conversion request")

                # Parse CIF
                parser = CifParser.from_str(request.cif_content)
                original_structure = parser.get_structures()[0]

                logger.info(f"✅ CIF parsed: {original_structure.composition.reduced_formula}")
                logger.info(f"   Original: {len(original_structure)} atoms")

                # Symmetry analysis
                analyzer = SpacegroupAnalyzer(original_structure, symprec=0.1, angle_tolerance=5.0)
                space_group = analyzer.get_space_group_symbol()
                space_group_number = analyzer.get_space_group_number()
                crystal_system = analyzer.get_crystal_system()

                logger.info(f"   Space group: {space_group} (No. {space_group_number})")
                logger.info(f"   Crystal system: {crystal_system}")

                # Convert to primitive or conventional
                if request.to_conventional:
                    structure = analyzer.get_conventional_standard_structure()
                    logger.info(f"   Conventional: {len(structure)} atoms")
                else:
                    structure = analyzer.get_primitive_standard_structure()
                    logger.info(f"   Primitive: {len(structure)} atoms")

                # Extract lattice parameters
                lattice = structure.lattice
                lattice_params = {
                    "a": float(lattice.a),
                    "b": float(lattice.b),
                    "c": float(lattice.c),
                    "alpha": float(lattice.alpha),
                    "beta": float(lattice.beta),
                    "gamma": float(lattice.gamma)
                }

                # Extract atoms (Cartesian coordinates)
                atoms = []
                for site in structure:
                    atoms.append({
                        "element": str(site.specie),
                        "position": [float(x) for x in site.coords],
                        "charge": 0
                    })

                # Build response
                response = StructureResponse(
                    formula=structure.composition.reduced_formula,
                    spaceGroup=space_group,
                    latticeParameters=lattice_params,
                    atoms=atoms,
                    properties={
                        "volume": float(lattice.volume),
                        "density": float(structure.density),
                        "isConventionalCell": request.to_conventional,
                        "numAtoms": len(structure),
                        "numSites": structure.num_sites,
                        "spaceGroupNumber": space_group_number,
                        "crystalSystem": crystal_system
                    }
                )

                logger.info(f"✅ Returning structure: {response.formula}, {len(atoms)} atoms")
                return response

            except Exception as e:
                logger.error(f"❌ CIF conversion failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"CIF conversion failed: {str(e)}"
                )

        @self.app.post("/api/parse_cif", response_model=StructureResponse)
        async def parse_cif(request: CIFConversionRequest):
            """
            Parse CIF file (alias for convert_to_conventional)

            This endpoint is used by the frontend to parse CIF files.
            It calls the same implementation as convert_to_conventional.
            """
            return await convert_to_conventional(request)

        @self.app.get("/api/download/{file_path:path}")
        async def download_file(file_path: str):
            """
            Download file from MCP Server papers directory

            Args:
                file_path: Relative path to the file (e.g., "papers/topic_xxx/file.csv")

            Returns:
                FileResponse with the file content
            """
            try:
                # 关键修复：记录下载请求信息
                logger.info(f"📥 Download request received")
                logger.info(f"   Original file_path: {file_path}")

                # Normalize path: remove ./ prefix, convert backslashes to forward slashes
                file_path = file_path.replace('\\', '/').lstrip('./')
                logger.info(f"   Normalized file_path: {file_path}")

                # Remove paper_search/ prefix if present
                if file_path.startswith('paper_search/'):
                    file_path = file_path[len('paper_search/'):]
                    logger.info(f"   Removed paper_search/ prefix: {file_path}")

                # Security: Only allow files from papers directory
                if not file_path.startswith("mcp_servers/paper_search/papers/"):
                    # Try to prepend the base path
                    if file_path.startswith("papers/"):
                        file_path = f"mcp_servers/paper_search/{file_path}"
                        logger.info(f"   Prepended base path: {file_path}")
                    else:
                        logger.error(f"❌ Access denied: {file_path}")
                        raise HTTPException(
                            status_code=403,
                            detail="Access denied: Only files from papers directory are allowed"
                        )

                # Check if file exists
                logger.info(f"   Checking if file exists: {file_path}")
                if not os.path.exists(file_path):
                    logger.error(f"❌ File not found: {file_path}")
                    logger.info(f"   Current working directory: {os.getcwd()}")
                    logger.info(f"   Absolute path: {os.path.abspath(file_path)}")
                    raise HTTPException(
                        status_code=404,
                        detail=f"File not found: {file_path}"
                    )

                # Check if it's a file (not a directory)
                if not os.path.isfile(file_path):
                    raise HTTPException(
                        status_code=400,
                        detail="Path is not a file"
                    )

                # Determine media type based on file extension
                filename = os.path.basename(file_path)
                media_type = "application/octet-stream"
                if filename.endswith('.csv'):
                    media_type = "text/csv"
                elif filename.endswith('.md'):
                    media_type = "text/markdown"
                elif filename.endswith('.json'):
                    media_type = "application/json"

                logger.info(f"✅ Downloading file: {file_path}")
                logger.info(f"   Media type: {media_type}")
                logger.info(f"   Filename: {filename}")
                logger.info(f"   File size: {os.path.getsize(file_path)} bytes")

                return FileResponse(
                    path=file_path,
                    media_type=media_type,
                    filename=filename
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ File download failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"File download failed: {str(e)}"
                )

    def get_app(self) -> FastAPI:
        """Get FastAPI application instance"""
        return self.app

    def _setup_upload_endpoints(self):
        """Setup file upload endpoints"""

        @self.app.post("/api/upload/structure", response_model=UploadResponse)
        async def upload_single_structure(file: UploadFile = File(...)):
            """
            Upload a single CIF file

            Args:
                file: CIF file

            Returns:
                UploadResponse with processed structure
            """
            try:
                # Validate file type
                if not file.filename or not file.filename.lower().endswith('.cif'):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid file type. Only .cif files are supported"
                    )

                # Read file content
                content = await file.read()
                if not content:
                    raise HTTPException(
                        status_code=400,
                        detail="Empty file provided"
                    )

                # 关键修复：记录接收到的内容大小
                logger.info(f"📥 Received file: {file.filename}, size: {len(content)} bytes")

                # Check file size
                if len(content) > self.MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {self.MAX_FILE_SIZE // (1024*1024)}MB"
                    )

                try:
                    cif_content = content.decode('utf-8')
                    # 关键修复：验证CIF内容的完整性
                    logger.info(f"✅ CIF content decoded successfully: {len(cif_content)} characters")
                    logger.debug(f"🔍 CIF content preview (first 200 chars): {cif_content[:200]}")
                    logger.debug(f"🔍 CIF content preview (last 200 chars): {cif_content[-200:]}")
                except UnicodeDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid file encoding. File must be UTF-8 encoded"
                    )

                # Parse CIF to extract formula using PyMatGen
                formula = "Unknown"
                try:
                    if PYMATGEN_AVAILABLE:
                        parser = CifParser.from_str(cif_content)
                        pmg_structure = parser.get_structures()[0]
                        formula = pmg_structure.composition.reduced_formula
                except Exception as e:
                    logger.warning(f"Failed to extract formula from CIF: {e}")

                # Convert CIF to structure
                logger.info(f"🔄 Converting CIF to structure format...")
                structure = StructureConverter.convert_cif_to_structure(
                    cif_content=cif_content,
                    name=file.filename.replace('.cif', ''),
                    composition=formula,
                    source="Upload"
                )

                if not structure:
                    logger.error(f"❌ Failed to convert CIF to structure")
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to parse CIF file"
                    )

                # 关键修复：验证转换后的结构完整性
                logger.info(f"✅ Structure converted successfully")
                logger.info(f"   Formula: {structure.get('formula', 'Unknown')}")
                logger.info(f"   Space Group: {structure.get('spaceGroup', 'Unknown')}")
                logger.info(f"   Atoms: {len(structure.get('atoms', []))}")
                logger.info(f"   Lattice Parameters: {structure.get('latticeParameters', {})}")
                logger.info(f"   CIF Content Length: {len(structure.get('cifContent', ''))}")

                # Mark as uploaded
                structure = StructureConverter.mark_as_uploaded(structure)

                logger.info(f"✅ Uploaded structure: {formula} from {file.filename}")
                logger.info(f"📋 Final structure source: {structure.get('source')}")
                logger.info(f"📋 Final structure metadata: {structure.get('metadata')}")

                return UploadResponse(
                    success=True,
                    message="Structure uploaded successfully",
                    structures=[structure],
                    count=1
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Upload failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Upload failed: {str(e)}"
                )

        @self.app.post("/api/upload/structures", response_model=UploadResponse)
        async def upload_multiple_structures(files: List[UploadFile] = File(...)):
            """
            Upload multiple CIF files

            Args:
                files: List of CIF files

            Returns:
                UploadResponse with processed structures
            """
            if not files:
                raise HTTPException(
                    status_code=400,
                    detail="No files provided"
                )
            
            # Check maximum number of files
            if len(files) > self.MAX_FILES_COUNT:
                raise HTTPException(
                    status_code=413,
                    detail=f"Too many files. Maximum is {self.MAX_FILES_COUNT} files per batch"
                )

            try:
                structures = []
                failed_files = []
                total_files = len(files)

                for file in files:
                    try:
                        # Validate file type
                        if not file.filename.lower().endswith('.cif'):
                            failed_files.append(f"{file.filename}: Invalid file type (must be .cif)")
                            continue

                        # Read file content
                        content = await file.read()
                        if not content:
                            failed_files.append(f"{file.filename}: Empty file")
                            continue

                        # 关键修复：记录接收到的内容大小
                        logger.info(f"📥 Received file: {file.filename}, size: {len(content)} bytes")

                        cif_content = content.decode('utf-8')
                        logger.info(f"✅ CIF content decoded: {len(cif_content)} characters")

                        # Parse CIF to extract formula
                        formula = "Unknown"
                        try:
                            if PYMATGEN_AVAILABLE:
                                parser = CifParser.from_str(cif_content)
                                pmg_structure = parser.get_structures()[0]
                                formula = pmg_structure.composition.reduced_formula
                        except Exception as e:
                            logger.warning(f"Failed to extract formula from {file.filename}: {e}")

                        # Convert CIF to structure
                        structure = StructureConverter.convert_cif_to_structure(
                            cif_content=cif_content,
                            name=file.filename.replace('.cif', ''),
                            composition=formula,
                            source="Upload"
                        )

                        if not structure:
                            failed_files.append(f"{file.filename}: Failed to parse CIF")
                            continue

                        # Mark as uploaded
                        structure = StructureConverter.mark_as_uploaded(structure)

                        structures.append(structure)
                        logger.info(f"✅ Uploaded structure: {formula} from {file.filename}")

                    except UnicodeDecodeError as e:
                        error_msg = f"{file.filename}: Invalid file encoding (must be UTF-8)"
                        failed_files.append(error_msg)
                        logger.error(f"❌ {error_msg}: {e}")
                    except Exception as e:
                        error_msg = f"{file.filename}: {str(e)}"
                        failed_files.append(error_msg)
                        logger.error(f"❌ Failed to process file {file.filename}: {e}")

                # Check if any structures were successfully processed
                if not structures:
                    error_detail = "All files failed to process"
                    if failed_files:
                        error_detail += f": {'; '.join(failed_files[:3])}"  # Show first 3 errors
                        if len(failed_files) > 3:
                            error_detail += f" and {len(failed_files) - 3} more errors"
                    
                    raise HTTPException(
                        status_code=400,
                        detail=error_detail
                    )

                # Prepare response message
                success_count = len(structures)
                failed_count = len(failed_files)
                
                if failed_count == 0:
                    message = f"Successfully uploaded all {success_count} structures"
                else:
                    message = f"Uploaded {success_count}/{total_files} structures successfully"
                    if failed_count <= 3:
                        message += f". Failed: {'; '.join(failed_files)}"
                    else:
                        message += f". {failed_count} files failed to process"

                return UploadResponse(
                    success=True,
                    message=message,
                    structures=structures,
                    count=success_count
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Upload failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Upload failed: {str(e)}"
                )

