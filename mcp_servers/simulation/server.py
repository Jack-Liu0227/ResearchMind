"""
Simulation MCP Server
Provides tools for computational simulation setup and analysis (VASP, Gaussian, LAMMPS).
Also provides MatterSim-based energy calculation, structure relaxation, and phonon calculation.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import os
from pathlib import Path
from urllib.parse import urlparse
import uuid
from dotenv import load_dotenv

# Add services directory to path for SessionManager
services_path = Path(__file__).parent.parent.parent / "services"
if str(services_path) not in sys.path:
    sys.path.insert(0, str(services_path))

# Load environment variables from ui/.env
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment variables from {env_path}")
else:
    print(f"WARNING: Environment file not found: {env_path}")

# Get API URL from environment variable
API_BASE_URL_RAW = (os.getenv('VITE_API_URL') or '').strip()


def _build_default_api_origin() -> str:
    host = os.getenv('RESEARCHMIND_HTTP_HOST', '127.0.0.1')
    port = os.getenv('RESEARCHMIND_HTTP_PORT', '50002')
    if host == '0.0.0.0':
        host = '127.0.0.1'
    return f'http://{host}:{port}'


def _resolve_api_base_url(candidate: str) -> str:
    if not candidate:
        return _build_default_api_origin()

    if candidate.startswith('/'):
        return _build_default_api_origin()

    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        return f'{parsed.scheme}://{parsed.netloc}'

    return _build_default_api_origin()


API_BASE_URL = _resolve_api_base_url(API_BASE_URL_RAW)
print(f"API Base URL: {API_BASE_URL}")

# 设置输出编码为UTF-8（解决Windows Unicode问题）
if os.name == 'nt':  # Windows
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

from fastmcp import FastMCP
import structlog

# Add modules directory to path
sys.path.insert(0, str(Path(__file__).parent / "modules"))

logger = structlog.get_logger(__name__)

# Import MatterSim energy calculation functions (optional)
MATTERSIM_AVAILABLE = False
MATTERSIM_IMPORT_ERROR = None
calculate_energy_from_cif_impl = None
relax_structure_impl = None
calculate_phonon_impl = None
from kappa_lib import ThermalConductivityCalculator, is_kappa_available

try:
    from mattersim_energy import (
        calculate_energy_from_cif_impl as _calc_energy,
        relax_structure_impl as _relax,
        calculate_phonon_impl as _phonon
    )
    calculate_energy_from_cif_impl = _calc_energy
    relax_structure_impl = _relax
    calculate_phonon_impl = _phonon
    MATTERSIM_AVAILABLE = True
except ImportError as e:
    MATTERSIM_IMPORT_ERROR = str(e)

# Import CIF tools
from cif_tools import calculate_kappa_from_cif_impl

# Import CrystaLLM generator
sys.path.insert(0, str(Path(__file__).parent / "crystallm"))
from generator import generate_crystal_from_composition

# Import SessionManager
try:
    # Add parent directory to path to import from services
    import sys
    from pathlib import Path
    services_path = str(Path(__file__).parent.parent.parent / "services")
    if services_path not in sys.path:
        sys.path.insert(0, services_path)

    from session_manager import SessionManager
    SESSION_MANAGER_AVAILABLE = True
    logger.info("SessionManager imported successfully")
except ImportError as e:
    logger.warning(f"SessionManager not available: {e}")
    SESSION_MANAGER_AVAILABLE = False


def _build_kappa_working_dir(session_id: Optional[str], prefix: str) -> Optional[Path]:
    """
    Build a session-scoped working directory for thermal conductivity runs.

    Args:
        session_id: Session identifier (optional)
        prefix: Directory name prefix (e.g., "single", "batch")

    Returns:
        Path to working directory or None if session isolation is not available.
    """
    if not (SESSION_MANAGER_AVAILABLE and session_id):
        return None

    base_dir = SessionManager.get_session_structures_dir(session_id) / "thermal_conductivity"
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Failed to prepare session thermal conductivity directory: {e}", session_id=session_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_suffix = uuid.uuid4().hex[:8]
    target_dir = base_dir / f"{prefix}_{timestamp}_{unique_suffix}"
    return target_dir

# Create FastMCP app
app = FastMCP("simulation")

# Health check will be handled by the HTTP server when running with uvicorn

# 全局变量存储最新生成的结构
latest_generated_structures = []






@app.tool
async def analyze_simulation_results(
    output_files: List[str],
    analysis_type: str = "energy"
) -> Dict[str, Any]:
    """
    Analyze simulation output files.
    
    Args:
        output_files: List of output file paths
        analysis_type: Type of analysis ("energy", "structure", "dynamics", "electronic")
    
    Returns:
        Dict containing analysis results
    """
    try:
        # Mock result analysis
        analysis = {
            "analysis_type": analysis_type,
            "input_files": output_files,
            "results": {},
            "timestamp": datetime.now().isoformat()
        }
        
        if analysis_type == "energy":
            analysis["results"] = {
                "final_energy": -123.456,
                "energy_convergence": True,
                "energy_change": 1.2e-6,
                "energy_plot": "energy_vs_steps.png",
                "statistics": {
                    "mean_energy": -123.456,
                    "std_dev": 0.001,
                    "min_energy": -123.460,
                    "max_energy": -123.450
                }
            }
        elif analysis_type == "structure":
            analysis["results"] = {
                "final_structure": "optimized_structure.xyz",
                "structural_changes": {
                    "max_displacement": 0.15,
                    "rms_displacement": 0.08,
                    "volume_change": -2.3
                },
                "symmetry_analysis": {
                    "initial_spacegroup": "Pm-3m",
                    "final_spacegroup": "Pm-3m",
                    "symmetry_preserved": True
                }
            }
        elif analysis_type == "dynamics":
            analysis["results"] = {
                "trajectory_file": "trajectory.xyz",
                "temperature_profile": "temperature_vs_time.png",
                "msd_analysis": {
                    "diffusion_coefficient": 2.3e-5,
                    "msd_plot": "msd_vs_time.png"
                },
                "radial_distribution": {
                    "rdf_file": "rdf.dat",
                    "first_peak": 2.86,
                    "coordination_number": 12.0
                }
            }
        elif analysis_type == "electronic":
            analysis["results"] = {
                "band_structure": "bands.png",
                "dos": "dos.png",
                "band_gap": {
                    "value": 1.23,
                    "type": "direct",
                    "units": "eV"
                },
                "fermi_level": -4.56,
                "electronic_density": "electron_density.cube"
            }
        
        logger.info("Simulation analysis completed", type=analysis_type, files=len(output_files))
        return analysis
        
    except Exception as e:
        logger.error("Simulation analysis failed", error=str(e))
        return {
            "error": str(e),
            "analysis_type": analysis_type,
            "timestamp": datetime.now().isoformat()
        }



# MatterSim-based tools
@app.tool
async def calculate_energy_from_cif(
    cif_content: str,
    cif_filename: str = "material.cif",
    device: str = "cuda"
) -> Dict[str, Any]:
    """
    Calculate energy properties from CIF file using MatterSim.

    ⚠️ 建议：为获得更准确的能量属性，建议先调用 relax_structure() 进行结构弛豫，然后使用弛豫后的 CIF 结构。

    Args:
        cif_content: CIF file content (base64 encoded or plain text) - 建议使用弛豫后的结构
        cif_filename: Original filename
        device: Computing device ('cuda' or 'cpu')

    Returns:
        Dict with energy properties and calculation results:
        - success: Whether calculation succeeded
        - energy: Total energy (eV)
        - formation_energy: Formation energy (eV/atom)
        - decomposition_energy: Energy above hull (eV/atom)
        - forces: Atomic forces (eV/Å)
        - stress: Stress tensor (GPa)
    """
    if not MATTERSIM_AVAILABLE:
        return {
            "success": False,
            "error": "MatterSim not available. Please install mattersim package."
        }

    return calculate_energy_from_cif_impl(cif_content, cif_filename, device)


@app.tool
async def relax_structure(
    cif_content: str,
    cif_filename: str = "material.cif",
    device: str = "cuda",
    optimizer: str = "BFGS",
    filter_type: str = "ExpCellFilter",
    constrain_symmetry: bool = True,
    max_steps: int = 500,
    fmax: float = 0.01
) -> Dict[str, Any]:
    """
    Perform structure relaxation using MatterSim.

    ⚠️ 重要：生成结构后必须先调用此工具进行结构弛豫，然后再进行声子谱计算或能量属性计算。

    Args:
        cif_content: CIF file content (base64 encoded or plain text)
        cif_filename: Original filename
        device: Computing device ('cuda' or 'cpu')
        optimizer: Optimization method ('BFGS', 'FIRE', 'LBFGS')
        filter_type: Filter to apply to the cell ('ExpCellFilter', 'FrechetCellFilter', None)
        constrain_symmetry: Whether to constrain the symmetry during relaxation
        max_steps: Maximum number of optimization steps
        fmax: Force convergence criterion (eV/Å)

    Returns:
        Dict with relaxed structure and relaxation results:
        - success: Whether relaxation succeeded
        - relaxed_cif: Relaxed structure in CIF format (use this for subsequent calculations)
        - initial_energy: Initial energy before relaxation
        - final_energy: Final energy after relaxation
        - energy_change: Energy change during relaxation
        - structure_changes: Structural changes (volume, lattice parameters)
    """
    if not MATTERSIM_AVAILABLE:
        return {
            "success": False,
            "error": "MatterSim not available. Please install mattersim package."
        }

    result = relax_structure_impl(
        cif_content, cif_filename, device, optimizer, filter_type,
        constrain_symmetry, max_steps, fmax
    )

    # If relaxation succeeded, convert relaxed structure to frontend format
    if result.get("success") and result.get("relaxed_cif_content"):
        try:
            from modules.cif_tools import convert_cif_to_frontend_structure

            # Convert relaxed CIF to frontend structure
            frontend_structure = convert_cif_to_frontend_structure(
                result["relaxed_cif_content"],
                result.get("composition", "Unknown"),
                source="Relaxed"
            )

            if frontend_structure:
                # Mark as relaxed structure
                if "source" not in frontend_structure:
                    frontend_structure["source"] = {}
                frontend_structure["source"]["database"] = "Relaxed"
                frontend_structure["source"]["isRelaxed"] = True

                # Add relaxation metadata
                if "metadata" not in frontend_structure:
                    frontend_structure["metadata"] = {}
                frontend_structure["metadata"]["relaxation"] = {
                    "initial_energy": result.get("initial_energy"),
                    "final_energy": result.get("final_energy"),
                    "energy_change": result.get("energy_change"),
                    "volume_change_percent": result.get("volume_change_percent"),
                    "converged": result.get("converged"),
                    "final_max_force": result.get("final_max_force")
                }

                # Add to result
                result["frontend_structures"] = [frontend_structure]
                logger.info(f"Relaxed structure converted to frontend format: {frontend_structure.get('formula')}")
        except Exception as e:
            logger.warning(f"WARNING: Failed to convert relaxed structure to frontend format: {e}")

    return result


@app.tool
async def calculate_phonon(
    cif_content: str,
    cif_filename: str = "material.cif",
    device: str = "cuda",
    supercell_matrix: Optional[List[int]] = None,
    amplitude: float = 0.01,
    find_prim: bool = False,
    session_id: str = None
) -> Dict[str, Any]:
    """
    Calculate phonon dispersion using MatterSim.

    Results are returned as base64-encoded images for direct display in frontend.
    No local files are saved - all temporary files are automatically cleaned up.

    ⚠️ 重要：计算声子谱前必须先调用 relax_structure() 进行结构弛豫，然后使用弛豫后的 CIF 结构。

    正确的工作流程：

    步骤 1 - 结构弛豫：
    ```python
    relax_result = await relax_structure(
        cif_content=original_cif_content,  # 原始 CIF 文件
        optimizer="BFGS",
        max_steps=500
    )
    ```

    步骤 2 - 计算声子谱（使用弛豫后的 CIF）：
    ```python
    if relax_result["success"]:
        phonon_result = await calculate_phonon(
            cif_content=relax_result["relaxed_cif_content"],  # ⚠️ 使用 relaxed_cif_content
            # 或者使用 base64 编码版本：
            # cif_content=relax_result["relaxed_cif_base64"],
            supercell_matrix=[4, 4, 4]
        )
    ```

    Args:
        cif_content: CIF file content (base64 encoded or plain text)
                    ⚠️ 必须使用 relax_structure() 返回的 relaxed_cif_content 或 relaxed_cif_base64
        cif_filename: Original filename
        device: Computing device ('cuda' or 'cpu')
        supercell_matrix: Supercell matrix for phonon calculation (default: [4, 4, 4])
        amplitude: Displacement amplitude for phonon calculation (default: 0.01 Å)
        find_prim: Whether to find primitive cell before calculation
        session_id: Session ID for data isolation (optional)

    Returns:
        Dict with phonon calculation results:
        - success: Whether calculation succeeded
        - has_imaginary_modes: Whether structure has imaginary phonon modes (unstable)
        - stability_status: "STABLE" or "UNSTABLE"
        - phonon_band_plot_base64: Base64-encoded phonon band structure plot (PNG)
        - phonon_band_plot_available: Whether band plot is available
        - phonon_dos_plot_base64: Base64-encoded phonon DOS plot (PNG)
        - phonon_dos_plot_available: Whether DOS plot is available
        - phonon_frequencies: Phonon frequency data
        - composition: Chemical composition
        - n_atoms: Number of atoms
    """
    if not MATTERSIM_AVAILABLE:
        return {
            "success": False,
            "error": "MatterSim not available. Please install mattersim package."
        }

    result = calculate_phonon_impl(
        cif_content, cif_filename, device, supercell_matrix,
        amplitude, find_prim
    )

    # 如果计算成功，将图片路径转换为前端格式（持久化存储方案）
    if result.get("success"):
        from pathlib import Path
        import shutil
        images = []

        # 确定保存目录
        if SESSION_MANAGER_AVAILABLE and session_id:
            # 使用会话目录
            phonon_dir = SessionManager.get_session_phonon_dir(session_id)
            # 使用相对路径，前端会自动解析为完整 URL
            url_prefix = f"/images/{session_id}/phonon_results"
            logger.info(f"📁 Using session phonon directory: {phonon_dir}")
        else:
            # 使用全局目录（向后兼容）
            phonon_dir = Path(__file__).parent / "phonon_results"
            # 使用相对路径，前端会自动解析为完整 URL
            url_prefix = f"/images/phonon_results"
            logger.info(f"📁 Using global phonon directory: {phonon_dir}")

        phonon_dir.mkdir(parents=True, exist_ok=True)

        # 处理声子色散图
        if result.get("phonon_band_plot_path") and result.get("phonon_band_plot_available"):
            src_path = Path(result["phonon_band_plot_path"])
            filename = src_path.name
            dest_path = phonon_dir / filename

            # 复制文件到会话目录 (如果不是同一个文件)
            if src_path.resolve() != dest_path.resolve():
                shutil.copy2(src_path, dest_path)
                logger.info(f"📋 Copied phonon band plot to: {dest_path}")
            else:
                logger.info(f"📋 Phonon band plot already in target directory: {dest_path}")

            images.append({
                "name": "phonon_dispersion.png",
                "path": str(dest_path),  # 会话目录中的路径
                "type": "phonon_dispersion",
                "url": f"{url_prefix}/{filename}",
                "filename": filename,
                "available": True  # 文件已保存,直接标记为可用
            })

        # 处理声子态密度图
        if result.get("phonon_dos_plot_path") and result.get("phonon_dos_plot_available"):
            src_path = Path(result["phonon_dos_plot_path"])
            filename = src_path.name
            dest_path = phonon_dir / filename

            # 复制文件到会话目录 (如果不是同一个文件)
            if src_path.resolve() != dest_path.resolve():
                shutil.copy2(src_path, dest_path)
                logger.info(f"📋 Copied phonon DOS plot to: {dest_path}")
            else:
                logger.info(f"📋 Phonon DOS plot already in target directory: {dest_path}")

            images.append({
                "name": "phonon_dos.png",
                "path": str(dest_path),  # 会话目录中的路径
                "type": "phonon_dos",
                "url": f"{url_prefix}/{filename}",
                "filename": filename,
                "available": True  # 文件已保存,直接标记为可用
            })

        # 添加图片数据到结果中
        if images:
            result["images"] = images
            if SESSION_MANAGER_AVAILABLE and session_id:
                logger.info(f"Phonon calculation completed, saved {len(images)} images to session {session_id}")
            else:
                logger.info(f"Phonon calculation completed, saved {len(images)} images to global directory")

    return result


# Health check endpoint
@app.tool
async def health_check() -> Dict[str, Any]:
    """
    Check the health of the simulation server.

    Returns:
        Dict containing server health information
    """
    return {
        "service": "simulation",
        "status": "healthy",
        "version": "2.0.0",
        "available_tools": [
            "setup_vasp_calculation",
            "setup_gaussian_calculation",
            "setup_lammps_simulation",
            "analyze_simulation_results",
            "monitor_job_status",
            "calculate_energy_from_cif",
            "relax_structure",
            "calculate_phonon",
            "generate_crystal_structure"
        ],
        "supported_software": ["VASP", "Gaussian", "LAMMPS", "MatterSim", "CrystaLLM"],
        "mattersim_available": MATTERSIM_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }


# CIF Tools
@app.tool
async def extract_and_validate_cif(
    session_id: str,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract and validate CIF file from uploaded files.

    **IMPORTANT**: User must upload CIF files first via the web interface.
    Files are automatically saved to the session's upload directory.
    This tool reads and validates those saved files.

    Args:
        session_id: Session ID (required) - identifies which session's uploads to read
        filename: Optional specific filename to validate. If not provided, will process all .cif files in the upload directory.

    Returns:
        Dict containing:
        - success: bool - Whether extraction and validation succeeded
        - cif_filename: str - Filename
        - file_path: str - Path to the saved CIF file
        - is_valid: bool - Whether CIF format is valid
        - error: str - Error message if failed

    Example:
        # User uploads a file via web interface, then you call:
        result = await extract_and_validate_cif(session_id="abc123", filename="structure.cif")
    """
    try:
        from pathlib import Path

        # Build upload directory path - use simulation/cif directory
        simulation_cif_dir = Path(__file__).parent / "cif"
        upload_dir = simulation_cif_dir / session_id / "uploads"

        if not upload_dir.exists():
            return {
                "success": False,
                "error": f"未找到 CIF 文件。",
                "is_valid": False
            }

        # Find CIF files
        if filename:
            cif_files = [upload_dir / filename]
            if not cif_files[0].exists():
                return {
                    "success": False,
                    "error": f"未找到文件 {filename}。请确保文件已上传。",
                    "is_valid": False
                }
        else:
            cif_files = list(upload_dir.glob("*.cif"))
            if not cif_files:
                return {
                    "success": False,
                    "error": f"上传目录中未找到 CIF 文件。请上传 .cif 文件。",
                    "is_valid": False
                }

        # Read and validate the first CIF file
        cif_file = cif_files[0]
        cif_content = cif_file.read_text(encoding='utf-8')
        cif_filename = cif_file.name

        logger.info(f"📂 Reading CIF file: {cif_file}")

        # Validate CIF content using existing implementation
        validation_result = _validate_cif_content(cif_content, cif_filename)
        validation_result["file_path"] = str(cif_file)
        validation_result["session_id"] = session_id

        return validation_result

    except Exception as e:
        logger.error(f"❌ Error extracting CIF: {e}")
        return {
            "success": False,
            "error": f"读取 CIF 文件失败: {str(e)}",
            "is_valid": False
        }


def _validate_cif_content(cif_content: str, filename: str) -> Dict[str, Any]:
    """
    Perform minimal validation of CIF file content.

    Philosophy: Only check for obvious errors (empty file, corrupted encoding).
    Let MatterSim/ASE handle detailed structure validation during actual calculations.
    This avoids false rejections of valid but non-standard CIF formats.

    Args:
        cif_content: CIF file content
        filename: Filename

    Returns:
        Validation result dict - always returns success=True unless file is obviously broken
    """
    try:
        # Basic sanity checks only

        # Check 1: File must not be empty
        if not cif_content or len(cif_content.strip()) == 0:
            return {
                "success": False,
                "cif_filename": filename,
                "is_valid": False,
                "error": "CIF 文件为空"
            }

        # Check 2: File must contain some text (not binary garbage)
        if not cif_content.isprintable() and not any(c in cif_content for c in ['\n', '\r', '\t']):
            return {
                "success": False,
                "cif_filename": filename,
                "is_valid": False,
                "error": "CIF 文件包含无效字符（可能是二进制文件）"
            }

        # Optional: Try to extract basic info for user feedback (but don't fail if this doesn't work)
        structure_info = None
        try:
            from ase.io import read
            from io import StringIO
            atoms = read(StringIO(cif_content), format='cif')

            structure_info = {
                "num_atoms": len(atoms),
                "formula": atoms.get_chemical_formula(),
                "cell_lengths": [round(x, 4) for x in atoms.get_cell_lengths_and_angles()[:3]],
                "cell_angles": [round(x, 2) for x in atoms.get_cell_lengths_and_angles()[3:]]
            }
            logger.info(f"✅ CIF preview: {structure_info['formula']}, {structure_info['num_atoms']} atoms")
        except Exception as e:
            # Don't fail - just log and continue
            logger.info(f"ℹ️ Could not extract structure info (will be validated during calculation): {e}")

        # Always return success - let MatterSim validate during calculation
        result = {
            "success": True,
            "cif_filename": filename,
            "is_valid": True,
            "file_size_kb": round(len(cif_content) / 1024, 2),
            "message": f"✅ CIF 文件已读取 ({round(len(cif_content) / 1024, 2)} KB)"
        }

        if structure_info:
            result["structure_info"] = structure_info
            result["message"] = f"✅ CIF 文件已读取 - {structure_info['formula']}, {structure_info['num_atoms']} 个原子"

        return result

    except Exception as e:
        # Only fail on catastrophic errors (file system issues, etc.)
        logger.error(f"❌ Unexpected error reading CIF file: {e}")
        return {
            "success": False,
            "cif_filename": filename,
            "is_valid": False,
            "error": f"读取文件时发生错误: {str(e)}"
        }


@app.tool
async def calculate_kappa_from_cif(
    cif_content,  # Can be str or List[Dict]
    cif_filename: str = "material.cif",
    method: str = "kappa_p",
    temperature: float = 300.0,
    session_id: Optional[str] = None,
    keep_files: bool = False
) -> Dict[str, Any]:
    """
    Calculate thermal conductivity from CIF file content.
    Supports both single CIF and batch calculation of multiple CIFs.

    This is the MAIN tool for thermal conductivity calculations from CIF files.
    It supports both Kappa-P (physics-based) and Kappa-MTP (ML-based) methods.

    Args:
        cif_content: SINGLE CIF: string content of CIF file (as string or base64)
                    BATCH: list of dicts with structure:
                    [{"cifContent": "...", "formula": "NaCl", "id": "struct1"}, ...]
        cif_filename: Name of the CIF file (default: "material.cif", used only for single CIF)
        method: Calculation method - "kappa_p" or "kappa_mtp" (default: "kappa_p")
        temperature: Temperature in Kelvin (default: 300K)
        session_id: Optional session identifier used to isolate intermediate files
        keep_files: Whether to keep generated CIF files for inspection

    Returns:
        SINGLE: Dict containing calculated thermal conductivity and results
        BATCH: Dict with summary, all results, and statistics
        
    Examples:
        # Single CIF
        result = await calculate_kappa_from_cif("data_crystal\\n...", method="kappa_p")
        
        # Batch CIFs
        structures = [
            {"cifContent": "data_NaCl\\n...", "formula": "NaCl", "id": "1"},
            {"cifContent": "data_GaN\\n...", "formula": "GaN", "id": "2"}
        ]
        result = await calculate_kappa_from_cif(structures, method="kappa_p")
    """
    working_dir_path = _build_kappa_working_dir(session_id, prefix="single")
    if working_dir_path:
        logger.info(
            "Using session-scoped working directory for thermal conductivity",
            session_id=session_id,
            working_dir=str(working_dir_path)
        )
    elif session_id and SESSION_MANAGER_AVAILABLE:
        logger.warning("Session ID provided but failed to build working directory", session_id=session_id)

    result = calculate_kappa_from_cif_impl(
        cif_content=cif_content,
        cif_filename=cif_filename,
        method=method,
        temperature=temperature,
        working_dir=str(working_dir_path) if working_dir_path else None,
        keep_files=keep_files
    )

    if keep_files and working_dir_path:
        result["working_directory"] = str(working_dir_path)

    return result


@app.tool
async def batch_calculate_kappa(
    structures: List[Dict[str, Any]],
    method: str = "kappa_p",
    temperature: float = 300.0,
    session_id: Optional[str] = None,
    keep_files: bool = False
) -> Dict[str, Any]:
    """
    批量计算多个结构的热导率 - 这是处理多个结构的主要工具。

    ⚠️ 重要：当有多个结构需要计算热导率时，必须使用此工具而不是多次调用单个计算工具。

    Args:
        structures: 结构列表，每个结构必须包含：
                   - cifContent 或 metadata.cifData: CIF 文件内容
                   - formula: 化学式（用于命名）
                   - id: 结构ID（可选）
        method: 计算方法 - "kappa_p" 或 "kappa_mtp" (默认: "kappa_p")
        temperature: 温度（开尔文，默认: 300K)
        session_id: 会话 ID，用于隔离临时文件（可选）
        keep_files: 是否保留中间生成的 CIF 文件（默认: False）

    Returns:
        Dict 包含：
        - success: 是否成功
        - total: 总结构数
        - completed: 成功计算的数量
        - failed: 失败的数量
        - results: 每个结构的计算结果列表
        - summary: 结果摘要

    Example:
        structures = [
            {"cifContent": "...", "formula": "NaCl", "id": "struct1"},
            {"cifContent": "...", "formula": "GaN", "id": "struct2"}
        ]
        result = await batch_calculate_kappa(structures, method="kappa_p")
    """
    logger.info(
        "🔄 Starting batch thermal conductivity calculation",
        structures=len(structures),
        method=method,
        temperature=temperature,
        session_id=session_id
    )

    working_dir_path = _build_kappa_working_dir(session_id, prefix="batch")
    if working_dir_path:
        logger.info(
            "Using session-scoped batch working directory",
            session_id=session_id,
            working_dir=str(working_dir_path)
        )
    elif session_id and SESSION_MANAGER_AVAILABLE:
        logger.warning("Session ID provided but failed to build batch working directory", session_id=session_id)

    batch_result = calculate_kappa_from_cif_impl(
        cif_content=structures,
        method=method,
        temperature=temperature,
        working_dir=str(working_dir_path) if working_dir_path else None,
        keep_files=keep_files
    )

    if keep_files and working_dir_path:
        batch_result["working_directory"] = str(working_dir_path)

    if batch_result.get("success"):
        response = {
            "success": True,
            "batch_mode": batch_result.get("batch_mode", True),
            "total": batch_result.get("total", len(structures)),
            "completed": batch_result.get("completed", 0),
            "failed": batch_result.get("failed", 0),
            "results": batch_result.get("results", []),
            "summary": batch_result.get("summary", {}),
            "timestamp": batch_result.get("timestamp", datetime.now().isoformat())
        }
        if keep_files and working_dir_path:
            response["working_directory"] = str(working_dir_path)
        return response

    return batch_result


@app.tool
async def generate_crystal_structure(
    composition: str,
    device: str = "cuda",
    num_samples: int = 1,
    top_k: int = 10,
    max_new_tokens: int = 2000
) -> Dict[str, Any]:
    """
    Generate crystal structure from chemical composition using CrystaLLM.

    This tool uses the CrystaLLM AI model to generate realistic crystal structures
    from a given chemical composition. The generated structures are in CIF format
    and can be used for further calculations (energy, thermal conductivity, etc.).

    Args:
        composition: Chemical composition (e.g., "Si", "GaN", "Fe2O3", "NaCl")
        device: Computing device ("cpu" or "cuda", default: "cuda")
        num_samples: Number of structures to generate (default: 1)
        top_k: Top-k sampling parameter for generation diversity (default: 10)
        max_new_tokens: Maximum tokens to generate (default: 2000)

    Returns:
        Dict containing:
        - success: bool - Whether generation succeeded
        - cif_content: str - Generated CIF file content
        - cif_filename: str - Generated CIF filename
        - composition: str - Input composition
        - generation_id: str - Unique generation ID
        - error: str - Error message if failed

    Example:
        result = await generate_crystal_structure(composition="GaN")
        if result["success"]:
            cif_content = result["cif_content"]
            # Use cif_content for further calculations
    """
    result = generate_crystal_from_composition(
        composition=composition,
        device=device,
        num_samples=num_samples,
        top_k=top_k,
        max_new_tokens=max_new_tokens
    )
    
    # 如果生成成功且包含frontend_structures，记录到全局缓存
    if result.get("success") and result.get("frontend_structures"):
        # 将结构数据存储到全局变量，供主服务器获取
        global latest_generated_structures
        latest_generated_structures = result["frontend_structures"]
        logger.info(f"Cached {len(latest_generated_structures)} frontend format structures")
        
        # 确保返回结果包含正确的字段名，以便主服务器可以识别
        result["structures"] = result["frontend_structures"]  # 添加structures字段作为备选
        logger.info(f"Structure generation completed: {result.get('composition')}, {len(result['frontend_structures'])} structures")
    
    return result

@app.tool
async def get_latest_generated_structures() -> Dict[str, Any]:
    """
    获取最新生成的晶体结构（前端格式）
    
    Returns:
        Dict containing:
        - success: bool - Whether structures are available
        - structures: List[Dict] - Frontend-compatible structure data
        - count: int - Number of structures
        - timestamp: str - Last generation timestamp
    """
    global latest_generated_structures
    
    if latest_generated_structures:
        return {
            "success": True,
            "structures": latest_generated_structures,
            "count": len(latest_generated_structures),
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "success": False,
            "structures": [],
            "count": 0,
            "message": "No structures generated yet",
            "timestamp": datetime.now().isoformat()
        }

@app.tool 
async def clear_structure_cache() -> Dict[str, Any]:
    """
    清空结构缓存
    
    Returns:
        Dict with operation status
    """
    global latest_generated_structures
    count = len(latest_generated_structures)
    latest_generated_structures = []
    
    return {
        "success": True,
        "message": f"Cleared {count} cached structures",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # import sys
    # # Configure logging to stderr (IMPORTANT: stdout is reserved for JSON-RPC messages in STDIO transport)
    # logging.basicConfig(
    #     level=logging.INFO,
    #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    #     stream=sys.stderr  # Output to stderr instead of stdout
    # )

    # # Configure structlog to output to stderr
    # structlog.configure(
    #     processors=[
    #         structlog.processors.add_log_level,
    #         structlog.processors.TimeStamper(fmt="iso"),
    #         structlog.dev.ConsoleRenderer()
    #     ],
    #     wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    #     context_class=dict,
    #     logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),  # Output to stderr
    #     cache_logger_on_first_use=True,
    # )

    # logger.info("Starting Simulation MCP Server")

    # # Log MatterSim availability
    # if MATTERSIM_AVAILABLE:
    #     logger.info("MatterSim modules loaded successfully")
    # else:
    #     logger.warning(f"MatterSim modules not available: {MATTERSIM_IMPORT_ERROR}. MatterSim tools will be disabled.")

    # # Run the server using SSE transport for better compatibility with Google ADK
    # # SSE transport is more stable and easier to debug than STDIO
    # import uvicorn

    # logger.info("Starting SSE server on 127.0.0.1:5003")
    # logger.info("SSE endpoint will be available at: http://127.0.0.1:5003/sse")

    import sys
    import warnings

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Suppress deprecation warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # Run in SSE mode
    import uvicorn
    # Get configuration from environment
    host = os.getenv("SIMULATION_MCP_HOST", "127.0.0.1")  # Bind to localhost by default
    port = int(os.getenv("SIMULATION_MCP_PORT", "50005"))
    external_url = os.getenv("SIMULATION_MCP_URL", f"http://127.0.0.1:{port}/sse")

    logger.info(f"[START] Starting Simulation MCP Server in SSE mode on http://{host}:{port}")
    logger.info("[INFO] Using SSE transport")
    logger.info(f"[INFO] External URL: {external_url}")
    logger.info(f"[INFO] Internal Endpoint: http://{host}:{port}/sse")

    # Create HTTP app
    http_app = app.http_app(transport="sse")
    
    # Add health check route using Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    
    async def health_check(request):
        """Health check endpoint for simulation MCP server"""
        return JSONResponse({
            "status": "healthy",
            "service": "simulation_mcp",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "mattersim_available": MATTERSIM_AVAILABLE,
            "kappa_available": is_kappa_available()
        })
    
    # Add health route to existing routes
    health_route = Route("/health", health_check, methods=["GET"])
    http_app.router.routes.append(health_route)
    
    # Use SSE transport explicitly with extended timeouts for long-running simulations
    uvicorn.run(
        http_app,
        host=host,
        port=port,
        log_level="info",
        reload=False,
        timeout_keep_alive=600,  # 增加到 10 分钟，适应声子计算等长时间任务
        timeout_graceful_shutdown=30,
        limit_concurrency=100,
        backlog=2048
    )
