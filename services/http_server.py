"""
HTTP API Server

Provides HTTP API endpoints for structure conversion, health checks, etc.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, RedirectResponse
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
    user_message: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


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

        # Setup billing and auth routes
        self._setup_billing_routes()

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

        @self.app.get("/api/")
        async def root():
            """API root endpoint"""
            return {
                "name": "ResearchMind API",
                "version": "1.0.0",
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "endpoints": {
                    "health": "/api/health",
                    "docs": "/api/docs",
                    "service_status": "/api/service_status",
                    "upload": "/api/upload",
                    "cif": "/api/cif",
                    "files": "/api/files?type=phonon_results|phonon_examples|generated_structures",
                    "images": "/api/images/{type}/{filename}",
                    "download_file": "/api/download/{file_path:path}"
                }
            }

        @self.app.get("/api/health", response_model=HealthResponse)
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

        # Compatibility: alias without /api prefix
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check_alias():
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
        
        @self.app.get("/api/files")
        async def list_files(type: str = "phonon_results"):
            """
            List available files by type

            Args:
                type: File type (phonon_results, phonon_examples, generated_structures)

            Returns:
                List of files with metadata
            """
            if type == "phonon_results":
                files = StaticFileService.list_phonon_results()
                return {
                    "success": True,
                    "type": "phonon_results",
                    "files": files,
                    "count": len(files),
                    "timestamp": datetime.now().isoformat()
                }
            elif type == "phonon_examples":
                files = StaticFileService.list_phonon_examples()
                return {
                    "success": True,
                    "type": "phonon_examples",
                    "files": files,
                    "count": len(files),
                    "timestamp": datetime.now().isoformat()
                }
            elif type == "generated_structures":
                files = StaticFileService.list_generated_structures()
                return {
                    "success": True,
                    "type": "generated_structures",
                    "files": files,
                    "count": len(files),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type: {type}. Must be one of: phonon_results, phonon_examples, generated_structures"
                )

        # 保留旧端点以兼容性（转发到新端点）
        @self.app.get("/api/phonon_results")
        async def list_phonon_results():
            """List available phonon result files (deprecated, use /api/files?type=phonon_results)"""
            files = StaticFileService.list_phonon_results()
            return {
                "success": True,
                "phonon_results": files,
                "count": len(files),
                "timestamp": datetime.now().isoformat()
            }

        @self.app.get("/api/phonon_examples")
        async def list_phonon_examples():
            """List phonon example files (deprecated, use /api/files?type=phonon_examples)"""
            files = StaticFileService.list_phonon_examples()
            return {
                "success": True,
                "files": files,
                "count": len(files),
                "timestamp": datetime.now().isoformat()
            }

        @self.app.get("/api/generated_structures")
        async def list_generated_structures():
            """List available generated structure files (deprecated, use /api/files?type=generated_structures)"""
            files = StaticFileService.list_generated_structures()
            return {
                "files": files,
                "count": len(files),
                "timestamp": datetime.now().isoformat()
            }
        
        # Note: /api/images/{image_type}/{filename} is handled by StaticFiles middleware
        # Do NOT add an API route here as it will override the static file serving

        @self.app.post("/api/cif", response_model=StructureResponse)
        async def cif_operation(request: CIFConversionRequest):
            """
            Unified CIF operation endpoint

            Supports:
            - action=parse: Parse CIF file (default)
            - action=convert_to_conventional: Convert to conventional cell
            - action=convert_to_primitive: Convert to primitive cell

            Args:
                request: CIF content and operation parameters

            Returns:
                Structure data
            """
            if not PYMATGEN_AVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="pymatgen not available, CIF conversion disabled"
                )

            try:
                logger.info("📥 Received CIF operation request")

                # Parse CIF - use parse_structures instead of deprecated get_structures
                parser = CifParser.from_str(request.cif_content)
                original_structure = parser.parse_structures(primitive=True)[0]

                logger.info(f"✅ CIF parsed: {original_structure.composition.reduced_formula}")
                logger.info(f"   Original: {len(original_structure)} atoms")

                # Symmetry analysis
                analyzer = SpacegroupAnalyzer(original_structure, symprec=0.1, angle_tolerance=5.0)
                space_group = analyzer.get_space_group_symbol()
                space_group_number = analyzer.get_space_group_number()
                crystal_system = analyzer.get_crystal_system()

                logger.info(f"   Space group: {space_group} (No. {space_group_number})")
                logger.info(f"   Crystal system: {crystal_system}")

                # Convert based on request
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
                logger.error(f"❌ CIF operation failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"CIF operation failed: {str(e)}"
                )

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

                # Parse CIF - use parse_structures instead of deprecated get_structures
                parser = CifParser.from_str(request.cif_content)
                original_structure = parser.parse_structures(primitive=True)[0]

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

        # Compatibility: alias without /api prefix
        @self.app.post("/cif", response_model=StructureResponse)
        async def cif_operation_alias(request: CIFConversionRequest):
            return await convert_to_conventional(request)

        # Robust download handlers that try both paper_search roots
        def _safe_join(base_dir: str, rel_path: str) -> Optional[str]:
            # Prevent path traversal and ensure within base_dir
            normalized = os.path.normpath(os.path.join(base_dir, rel_path))
            if os.path.commonpath([os.path.abspath(normalized), os.path.abspath(base_dir)]) == os.path.abspath(base_dir):
                return normalized
            return None

        def _find_download_file(file_path: str) -> Optional[str]:
            roots = [
                os.path.join(server_config.STATIC_FILES_ROOT, "mcp_servers", "paper_search"),
                os.path.join(server_config.STATIC_FILES_ROOT, "mcp_servers", "mcp_servers", "paper_search"),
            ]
            for root in roots:
                candidate = _safe_join(root, file_path)
                if candidate and os.path.isfile(candidate):
                    return candidate
            return None

        @self.app.get("/api/download/{file_path:path}")
        async def download_file_api(file_path: str):
            full = _find_download_file(file_path)
            if not full:
                raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
            return FileResponse(full)

        @self.app.get("/download/{file_path:path}")
        async def download_file_legacy(file_path: str):
            full = _find_download_file(file_path)
            if not full:
                raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
            return FileResponse(full)

        # Compatibility: alias without /api prefix
        @self.app.post("/cif", response_model=StructureResponse)
        async def cif_operation_alias(request: CIFConversionRequest):
            return await convert_to_conventional(request)

        # NOTE: /api/download/{file_path:path} 路由已移至静态文件挂载
        # 在 StaticFileService.setup_static_files() 中通过以下方式处理：
        # app.mount("/api/download", StaticFiles(directory=papers_dir), name="papers_download")
        # 这样可以直接提供 CSV 和 MD 文件，无需额外的路由处理

        # Removed legacy redirect to avoid 307 loops; now handled by StaticFiles mount at /download

    def get_app(self) -> FastAPI:
        """Get FastAPI application instance"""
        return self.app

    def _setup_billing_routes(self):
        """Setup billing and OAuth authentication routes"""
        try:
            from services.billing_api import router as billing_router, auth_router
            self.app.include_router(billing_router)
            self.app.include_router(auth_router)
            logger.info("✅ Billing and OAuth routes registered")
        except Exception as e:
            logger.warning(f"⚠️ Failed to register billing routes: {e}")

    def _setup_upload_endpoints(self):
        """Setup file upload endpoints"""

        @self.app.post("/api/upload")
        async def unified_upload(
            files: List[UploadFile] = File(...),
            type: str = "structure",
            user_message: Optional[str] = Form(None)
        ):
            """
            Unified upload endpoint supporting multiple file types

            Args:
                files: Files to upload
                type: Upload type (structure, structures, documents)

            Returns:
                Upload response with processed files
            """
            if not files:
                raise HTTPException(status_code=400, detail="No files provided")

            # Route to appropriate handler based on type
            if type in ["structure", "structures"]:
                # Handle CIF structure uploads
                if len(files) == 1 and type == "structure":
                    # Single file upload
                    return await upload_single_structure(files[0], user_message=user_message)
                else:
                    # Multiple files upload
                    return await upload_multiple_structures(files, user_message=user_message)
            elif type == "documents":
                # Handle document uploads
                return await upload_documents(files=files)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid upload type: {type}. Must be one of: structure, structures, documents"
                )

        @self.app.post("/api/upload/structure", response_model=UploadResponse)
        async def upload_single_structure(
            file: UploadFile = File(...),
            user_message: Optional[str] = Form(None)
        ):
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

                # Convert CIF to structure (StructureConverter will handle PyMatGen analysis)
                # This avoids duplicate processing
                logger.info(f"🔄 Converting CIF to structure format...")
                structure = StructureConverter.convert_cif_to_structure(
                    cif_content=cif_content,
                    name=file.filename.replace('.cif', ''),
                    composition="Unknown",  # Will be extracted by StructureConverter
                    source="Upload"
                )

                logger.info(f"✅ Structure conversion completed")

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

                # Prepare attachment payload so frontend can forward to agent via WebSocket
                attachment = {
                    "filename": file.filename,
                    "content": cif_content
                }

                return UploadResponse(
                    success=True,
                    message="Structure uploaded successfully",
                    structures=[structure],
                    count=1,
                    user_message=user_message,
                    attachments=[attachment]
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Upload failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Upload failed: {str(e)}"
                )

        @self.app.post("/api/upload/documents")
        async def upload_documents(
            files: List[UploadFile] = File(...),
            session_id: Optional[str] = None,
            topic: Optional[str] = None,
        ):
            """Upload and ingest documents (PDF/DOC/TXT/MD) into paper entries.

            Uses paper_search ingestion to extract text (PDF via PyPDF2 if available),
            persists session metadata, and returns CSV + per-file download links.
            """
            if not files:
                raise HTTPException(status_code=400, detail="No files provided")

            try:
                from mcp_servers.paper_search.modules.paper_manager.uploaded_documents import ingest_uploaded_documents
                from mcp_servers.paper_search.server import get_download_url

                norm_files: List[Dict[str, Any]] = []
                for f in files:
                    content_bytes = await f.read()
                    if not content_bytes:
                        continue
                    import base64
                    b64 = base64.b64encode(content_bytes).decode("utf-8")
                    norm_files.append({
                        "filename": f.filename,
                        "encoding": "base64",
                        "mime_type": f.content_type,
                        "content": b64,
                    })

                if not norm_files:
                    raise HTTPException(status_code=400, detail="All files are empty")

                import uuid
                if not session_id:
                    session_id = "upload_" + uuid.uuid4().hex[:8]
                topic = topic or "uploaded_documents"

                result = ingest_uploaded_documents(files=norm_files, session_id=session_id, topic=topic)
                if result.get("status") != "success":
                    raise HTTPException(status_code=500, detail=result.get("error", "Ingestion failed"))

                payload: Dict[str, Any] = {
                    "status": "success",
                    "session_id": result.get("session_id"),
                    "topic": result.get("topic"),
                    "papers": result.get("papers", []),
                    "uploaded_files": [],
                }

                csv_path = (result.get("csv_result") or {}).get("file_path")
                if csv_path:
                    try:
                        payload["csv_download_url"] = get_download_url(csv_path)
                        payload["csv_file_path"] = csv_path
                    except Exception:
                        payload["csv_file_path"] = csv_path

                for item in result.get("uploaded_files", []):
                    saved_path = item.get("saved_path")
                    download_url = None
                    if saved_path:
                        try:
                            download_url = get_download_url(saved_path)
                        except Exception:
                            download_url = None
                    payload["uploaded_files"].append({
                        "paper_id": item.get("paper_id"),
                        "filename": item.get("filename"),
                        "file_path": saved_path,
                        "download_url": download_url,
                    })

                return payload
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to ingest documents: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/upload/structures", response_model=UploadResponse)
        async def upload_multiple_structures(
            files: List[UploadFile] = File(...),
            user_message: Optional[str] = Form(None)
        ):
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

                        # Convert CIF to structure (StructureConverter will extract formula)
                        logger.info(f"🔄 Converting {file.filename} to structure format...")
                        structure = StructureConverter.convert_cif_to_structure(
                            cif_content=cif_content,
                            name=file.filename.replace('.cif', ''),
                            composition="Unknown",  # Will be extracted by StructureConverter
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

                # Build attachments for successfully processed structures
                atts: List[Dict[str, Any]] = []
                try:
                    for s, f in zip(structures, files):
                        # Only include attachment if structure parsed
                        try:
                            # We don't store the original content; re-read here
                            # Note: UploadFile stream is consumed; fallback to cifContent in structure
                            content_text = s.get('cifContent') or ''
                            atts.append({"filename": f.filename, "content": content_text})
                        except Exception:
                            continue
                except Exception:
                    atts = []

                return UploadResponse(
                    success=True,
                    message=message,
                    structures=structures,
                    count=success_count,
                    user_message=user_message,
                    attachments=atts
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Upload failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Upload failed: {str(e)}"
                )

