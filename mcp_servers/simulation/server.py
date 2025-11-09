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

# Import storage manager
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.storage_manager import get_session_storage_path


def _get_cif_file_path(session_id: str, cif_filename: str) -> Optional[Path]:
    """
    获取 CIF 文件路径（统一存储）

    优先级：
    1. session_data/simulation/{session_id}/relaxed_structures/{cif_filename}
    2. session_data/simulation/{session_id}/cif/{cif_filename}
    3. session_data/simulation/{session_id}/uploads/{cif_filename}
    4. session_data/simulation/{session_id}/generated_structures/**/{cif_filename}  # 🆕 支持生成的结构（递归查找）
    5. 旧路径（向后兼容）: mcp_servers/simulation/cif/{session_id}/relax/{cif_filename}
    6. 旧路径（向后兼容）: mcp_servers/simulation/cif/{session_id}/uploads/{cif_filename}

    Args:
        session_id: 会话ID
        cif_filename: CIF文件名

    Returns:
        CIF文件路径，如果不存在返回None
    """
    # 尝试新的统一存储路径（直接查找）
    for data_type in ["relaxed_structures", "cif", "uploads"]:
        try:
            storage_path = get_session_storage_path(session_id, data_type, create=False)
            cif_path = storage_path / cif_filename
            if cif_path.exists():
                logger.info(f"✅ Found CIF file in unified storage ({data_type}): {cif_path}")
                return cif_path
        except Exception as e:
            logger.debug(f"Failed to check {data_type}: {e}")

    # 🔧 特殊处理 generated_structures：递归查找子目录
    # 因为生成的结构保存在 generated/{composition}_{generation_id}/generated/ 或 processed/ 下
    try:
        generated_base = get_session_storage_path(session_id, "generated_structures", create=False)
        if generated_base.exists():
            # 使用 glob 递归查找文件
            for cif_path in generated_base.rglob(cif_filename):
                if cif_path.is_file():
                    logger.info(f"✅ Found CIF file in generated_structures (recursive): {cif_path}")
                    return cif_path
    except Exception as e:
        logger.debug(f"Failed to check generated_structures: {e}")

    # 尝试旧路径（向后兼容）
    simulation_cif_dir = Path(__file__).parent / "cif"
    for subdir in ["relax", "uploads"]:
        cif_path = simulation_cif_dir / session_id / subdir / cif_filename
        if cif_path.exists():
            logger.warning(f"⚠️ Found CIF file in legacy path: {cif_path}")
            return cif_path

    return None


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
    session_id: str,
    cif_filename: str,
    device: str = "cuda"
) -> Dict[str, Any]:
    """
    Calculate energy properties from CIF file using MatterSim.

    ⚠️ 建议：为获得更准确的能量属性，建议先调用 relax_structure() 进行结构弛豫，然后使用弛豫后的 CIF 文件。

    Args:
        session_id: Session ID (required) - identifies which session's CIF file to use
        cif_filename: CIF filename in the session directory (建议使用弛豫后的文件)
        device: Computing device ('cuda' or 'cpu')

    Returns:
        Dict with energy properties and calculation results:
        - success: Whether calculation succeeded
        - energy: Total energy (eV)
        - formation_energy: Formation energy (eV/atom)
        - decomposition_energy: Energy above hull (eV/atom)
        - forces: Atomic forces (eV/Å)
        - stress_tensor_gpa: Full 3×3 stress tensor (GPa) - ~200 tokens
        - pressure_gpa: Scalar hydrostatic pressure (GPa)

        Note: Full stress tensor is returned for detailed analysis. If token optimization
        is critical, consider using only pressure_gpa for scalar stress information.

    Example:
        # After relaxation:
        result = await calculate_energy_from_cif(
            session_id="abc123",
            cif_filename="relaxed_structure_20251105_220000.cif"
        )
    """
    if not MATTERSIM_AVAILABLE:
        return {
            "success": False,
            "error": "MatterSim not available. Please install mattersim package."
        }

    # Read CIF file from session directory (using unified storage)
    try:
        cif_path = _get_cif_file_path(session_id, cif_filename)

        if not cif_path:
            return {
                "success": False,
                "error": f"CIF file not found: {cif_filename}. Please ensure the file exists in session {session_id}."
            }

        cif_content = cif_path.read_text(encoding='utf-8')
        logger.info(f"📂 Read CIF file for energy calculation: {cif_path}")

    except Exception as e:
        logger.error(f"❌ Failed to read CIF file: {e}")
        return {
            "success": False,
            "error": f"Failed to read CIF file: {str(e)}"
        }

    return calculate_energy_from_cif_impl(cif_content, cif_filename, device)


@app.tool
async def relax_structure(
    session_id: str,
    cif_filename: str,
    device: str = "cuda",
    optimizer: str = "BFGS",
    filter_type: str = "ExpCellFilter",
    constrain_symmetry: bool = True,
    max_steps: int = 500,
    fmax: float = 0.01
) -> Dict[str, Any]:
    """
    Perform structure relaxation using MatterSim.

    ⚠️ 重要：
    1. 用户必须先上传 CIF 文件到 session
    2. 生成结构后必须先调用此工具进行结构弛豫
    3. 然后再进行声子谱计算或能量属性计算

    Args:
        session_id: Session ID (required) - identifies which session's CIF file to use
        cif_filename: CIF filename in the session's upload directory (e.g., "structure.cif")
        device: Computing device ('cuda' or 'cpu')
        optimizer: Optimization method ('BFGS', 'FIRE', 'LBFGS')
        filter_type: Filter to apply to the cell ('ExpCellFilter', 'FrechetCellFilter', None)
        constrain_symmetry: Whether to constrain the symmetry during relaxation
        max_steps: Maximum number of optimization steps
        fmax: Force convergence criterion (eV/Å)

    Returns:
        Dict with relaxed structure and relaxation results:
        - success: Whether relaxation succeeded
        - relaxed_cif_file: Path to saved relaxed CIF file
        - relaxed_cif_url: URL to access the relaxed CIF file
        - relaxed_cif_filename: Filename of the relaxed CIF
        - frontend_structures: List with relaxed structure in frontend format (includes cifContent for visualization)
        - initial_energy: Initial energy before relaxation
        - final_energy: Final energy after relaxation
        - energy_change: Energy change during relaxation
        - structure_changes: Structural changes (volume, lattice parameters)

        ⚠️ TOKEN OPTIMIZATION: CIF content is NOT returned in the response to reduce token consumption by ~95%.
        Instead, use:
        - relaxed_cif_file: File path for downstream calculations
        - relaxed_cif_url: URL for downloading the CIF file
        - frontend_structures[0].cifContent: CIF content for frontend visualization

    Example:
        # User uploads structure.cif via web interface, then:
        result = await relax_structure(
            session_id="abc123",
            cif_filename="structure.cif",
            optimizer="BFGS"
        )
    """
    if not MATTERSIM_AVAILABLE:
        return {
            "success": False,
            "error": "MatterSim not available. Please install mattersim package."
        }

    # Read CIF file from session directory (using unified storage)
    try:
        cif_path = _get_cif_file_path(session_id, cif_filename)

        if not cif_path:
            return {
                "success": False,
                "error": f"CIF file not found: {cif_filename}. Please ensure the file has been uploaded to session {session_id}."
            }

        cif_content = cif_path.read_text(encoding='utf-8')
        logger.info(f"📂 Read CIF file from session: {cif_path}")

    except Exception as e:
        logger.error(f"❌ Failed to read CIF file: {e}")
        return {
            "success": False,
            "error": f"Failed to read CIF file: {str(e)}"
        }

    result = relax_structure_impl(
        cif_content, cif_filename, device, optimizer, filter_type,
        constrain_symmetry, max_steps, fmax
    )

    # If relaxation succeeded, save the relaxed CIF to session directory
    if result.get("success") and result.get("relaxed_cif_content"):
        try:
            from pathlib import Path
            from datetime import datetime

            # Determine save directory - use unified storage
            if session_id:
                # Save to session-specific relaxed directory (unified storage)
                structures_dir = get_session_storage_path(
                    session_id=session_id,
                    data_type="relaxed_structures",
                    create=True
                )
                url_prefix = f"/structures/{session_id}/relaxed"
                logger.info(f"📁 Using unified storage relaxed directory: {structures_dir}")
            else:
                # Use global directory (backward compatibility)
                structures_dir = Path(__file__).parent / "relaxed_structures"
                structures_dir.mkdir(exist_ok=True)
                url_prefix = "/structures/relaxed"
                logger.info(f"📁 Using global structures directory: {structures_dir}")

            # Generate filename for relaxed structure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = Path(cif_filename).stem
            relaxed_filename = f"relaxed_{base_name}_{timestamp}.cif"
            relaxed_file_path = structures_dir / relaxed_filename

            # Save relaxed CIF to file
            with open(relaxed_file_path, 'w', encoding='utf-8') as f:
                f.write(result["relaxed_cif_content"])

            logger.info(f"💾 Saved relaxed CIF to: {relaxed_file_path}")

            # Update result with file path and URL
            result["relaxed_cif_file"] = str(relaxed_file_path)
            result["relaxed_cif_url"] = f"{url_prefix}/{relaxed_filename}"
            result["relaxed_cif_filename"] = relaxed_filename

            logger.info(f"✅ Relaxed structure saved and ready for phonon/thermal calculations")
            logger.info(f"   📄 Filename: {relaxed_filename}")
            logger.info(f"   📂 Path: {relaxed_file_path}")
            logger.info(f"   🔗 URL: {result['relaxed_cif_url']}")

            # Convert relaxed structure to frontend format for visualization
            from modules.cif_tools import convert_cif_to_frontend_structure

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
                logger.info(f"✅ Relaxed structure converted to frontend format: {frontend_structure.get('formula')}")

            # ⚠️ TOKEN OPTIMIZATION: Remove large CIF content to reduce token consumption by ~95%
            # CIF content is now saved to file and accessible via file path/URL
            if "relaxed_cif_content" in result:
                del result["relaxed_cif_content"]
            if "relaxed_cif_base64" in result:
                del result["relaxed_cif_base64"]

            # Add optimization note
            result["token_optimization"] = {
                "cif_content_removed": True,
                "reason": "CIF content saved to file to optimize token usage (~95% reduction)",
                "access_via": "Use relaxed_cif_file, relaxed_cif_url, or frontend_structures"
            }

        except Exception as e:
            logger.warning(f"⚠️ Failed to save/convert relaxed structure: {e}")
            # Don't fail the entire operation, just log the warning

    return result


@app.tool
async def calculate_phonon_from_directory(
    cif_directory: str,
    device: str = "cuda",
    supercell_matrix: Optional[List[int]] = None,
    amplitude: float = 0.01,
    find_prim: bool = False,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    批量计算文件夹中所有 CIF 文件的声子谱。

    ⚠️ 推荐：当有多个弛豫后的 CIF 文件需要计算声子谱时，使用此工具批量计算。

    Args:
        cif_directory: 包含 CIF 文件的文件夹路径（绝对路径或相对于项目根目录）
                      例如: "mcp_servers/simulation/cif/session_xxx/relax"
        device: 计算设备 ('cuda' 或 'cpu')
        supercell_matrix: 超胞矩阵 (默认: [4, 4, 4])
        amplitude: 位移幅度 (默认: 0.01 Å)
        find_prim: 是否在计算前寻找原胞
        session_id: 会话 ID（可选，用于结果文件命名）

    Returns:
        Dict 包含：
        - success: 是否成功
        - total: 总结构数
        - completed: 成功计算的数量
        - failed: 失败的数量
        - results: 每个结构的计算结果列表
        - summary: 结果摘要

    Example:
        result = await calculate_phonon_from_directory(
            cif_directory="mcp_servers/simulation/cif/session_xxx/relax",
            supercell_matrix=[4, 4, 4]
        )
    """
    if not MATTERSIM_AVAILABLE:
        return {
            "success": False,
            "error": "MatterSim not available. Please install mattersim package."
        }

    try:
        # Validate directory exists
        cif_dir = Path(cif_directory)
        if not cif_dir.exists():
            return {
                "success": False,
                "error": f"Directory not found: {cif_directory}",
                "timestamp": datetime.now().isoformat()
            }

        if not cif_dir.is_dir():
            return {
                "success": False,
                "error": f"Path is not a directory: {cif_directory}",
                "timestamp": datetime.now().isoformat()
            }

        # Find all CIF files in directory
        cif_files = list(cif_dir.glob('*.cif')) + list(cif_dir.glob('*.CIF'))

        if not cif_files:
            return {
                "success": False,
                "error": f"No CIF files found in directory: {cif_directory}",
                "total": 0,
                "timestamp": datetime.now().isoformat()
            }

        logger.info(f"📁 Found {len(cif_files)} CIF files for phonon calculation in {cif_directory}")

        # Calculate phonon for each CIF file
        results = []
        completed = 0
        failed = 0

        for i, cif_file in enumerate(cif_files, 1):
            logger.info(f"🔄 Processing {i}/{len(cif_files)}: {cif_file.name}")

            try:
                cif_content = cif_file.read_text(encoding='utf-8')

                # Call phonon calculation implementation
                from modules.mattersim_energy import calculate_phonon_impl

                # Determine output directory for phonon results - use unified storage
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from shared.storage_manager import get_session_storage_path
                phonon_dir = get_session_storage_path(
                    session_id=session_id or "default",
                    data_type="phonon_results",
                    create=True
                )

                result = calculate_phonon_impl(
                    cif_content=cif_content,
                    cif_filename=cif_file.name,
                    device=device,
                    supercell_matrix=supercell_matrix or [4, 4, 4],
                    amplitude=amplitude,
                    find_prim=find_prim,
                    output_dir=str(phonon_dir)
                )

                if result.get("success"):
                    completed += 1
                    logger.info(f"✅ Completed {i}/{len(cif_files)}: {cif_file.name}")
                else:
                    failed += 1
                    logger.warning(f"❌ Failed {i}/{len(cif_files)}: {cif_file.name} - {result.get('error', 'Unknown error')}")

                results.append({
                    "filename": cif_file.name,
                    "index": i,
                    **result
                })

            except Exception as e:
                failed += 1
                logger.error(f"❌ Error processing {cif_file.name}: {e}")
                results.append({
                    "filename": cif_file.name,
                    "index": i,
                    "success": False,
                    "error": str(e)
                })

        return {
            "success": completed > 0,
            "total": len(cif_files),
            "completed": completed,
            "failed": failed,
            "results": results,
            "summary": {
                "total_structures": len(cif_files),
                "successful": completed,
                "failed": failed,
                "success_rate": f"{(completed/len(cif_files)*100):.1f}%" if cif_files else "0%"
            }
        }

    except Exception as e:
        logger.error(f"Error in batch phonon calculation from directory: {e}")
        return {
            "success": False,
            "error": f"Batch phonon calculation failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@app.tool
async def calculate_phonon(
    session_id: str,
    cif_filename: str,
    device: str = "cuda",
    supercell_matrix: Optional[List[int]] = None,
    amplitude: float = 0.01,
    find_prim: bool = False
) -> Dict[str, Any]:
    """
    Calculate phonon dispersion using MatterSim for a single CIF file.

    Results are saved as image files and returned with URLs for frontend display.

    ⚠️ 重要工作流程：
    1. 用户上传原始 CIF 文件
    2. 调用 relax_structure() 进行结构弛豫
    3. 使用弛豫后的 CIF 文件名调用此函数计算声子谱

    ⚠️ 批量计算：如果需要计算多个 CIF 文件的声子谱，请使用 calculate_phonon_from_directory 工具

    正确的调用顺序：

    步骤 1 - 结构弛豫：
    ```python
    relax_result = await relax_structure(
        session_id="abc123",
        cif_filename="structure.cif",  # 原始上传的文件
        optimizer="BFGS"
    )
    ```

    步骤 2 - 计算声子谱（使用弛豫后的文件）：
    ```python
    if relax_result["success"]:
        phonon_result = await calculate_phonon(
            session_id="abc123",
            cif_filename=relax_result["relaxed_cif_filename"],  # ⚠️ 使用弛豫后的文件名
            supercell_matrix=[4, 4, 4]
        )
    ```

    Args:
        session_id: Session ID (required) - identifies which session's CIF file to use
        cif_filename: CIF filename in the session directory (e.g., "relaxed_structure_20251105_220000.cif")
                     ⚠️ 应该使用 relax_structure() 返回的 relaxed_cif_filename
        device: Computing device ('cuda' or 'cpu')
        supercell_matrix: Supercell matrix for phonon calculation (default: [4, 4, 4])
        amplitude: Displacement amplitude for phonon calculation (default: 0.01 Å)
        find_prim: Whether to find primitive cell before calculation

    Returns:
        Dict with phonon calculation results:
        - success: Whether calculation succeeded
        - has_imaginary_modes: Whether structure has imaginary phonon modes (unstable)
        - stability_status: "STABLE" or "UNSTABLE"
        - images: List of image objects with URLs for frontend display
        - phonon_data_file: Path to JSON file containing full phonon frequency data
        - phonon_summary: Summary statistics (has_imaginary_modes, num_frequencies, min/max frequency)

        ⚠️ TOKEN OPTIMIZATION: Full phonon frequency data is NOT returned in the response (~90% reduction).
        Instead, use:
        - phonon_data_file: Path to JSON file with complete frequency data
        - phonon_dispersion_csv: Path to CSV file with dispersion data (q-points × frequencies)
        - phonon_dos_csv: Path to CSV file with DOS data (frequency × density)
        - phonon_summary: Key statistics for quick reference
        - images: Phonon band structure and DOS plots for visualization
        - composition: Chemical composition
        - n_atoms: Number of atoms

    Example:
        result = await calculate_phonon(
            session_id="abc123",
            cif_filename="relaxed_C_20251105_220000.cif",
            supercell_matrix=[4, 4, 4]
        )
    """
    if not MATTERSIM_AVAILABLE:
        return {
            "success": False,
            "error": "MatterSim not available. Please install mattersim package."
        }

    # Read CIF file from session directory (using unified storage)
    try:
        cif_path = _get_cif_file_path(session_id, cif_filename)

        if not cif_path:
            return {
                "success": False,
                "error": f"CIF file not found: {cif_filename}. Please ensure the file exists in session {session_id}. "
                        f"For phonon calculations, you should use the relaxed CIF file from relax_structure()."
            }

        cif_content = cif_path.read_text(encoding='utf-8')
        logger.info(f"📂 Read CIF file for phonon calculation: {cif_path}")

    except Exception as e:
        logger.error(f"❌ Failed to read CIF file: {e}")
        return {
            "success": False,
            "error": f"Failed to read CIF file: {str(e)}"
        }

    # 确定图片保存目录（在调用 impl 之前）- 使用统一存储
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from shared.storage_manager import get_session_storage_path

    # 使用统一的 session_data 目录
    phonon_dir = get_session_storage_path(
        session_id=session_id or "default",
        data_type="phonon_results",
        create=True
    )
    # 🔧 修复：生成正确的 URL 前缀，包含 session_id 和 phonon_results 路径
    # 挂载点: /api/images/phonon -> session_data/simulation/
    # 文件路径: session_data/simulation/{session_id}/phonon_results/file.png
    # URL: /api/images/phonon/{session_id}/phonon_results/file.png
    url_prefix = f"/api/images/phonon/{session_id or 'default'}/phonon_results"
    logger.info(f"📁 Target phonon directory: {phonon_dir}")
    logger.info(f"🔗 URL prefix: {url_prefix}")

    # 调用实现函数，传入目标目录以避免重复保存
    result = calculate_phonon_impl(
        cif_content, cif_filename, device, supercell_matrix,
        amplitude, find_prim, output_dir=str(phonon_dir)
    )

    # 如果计算成功，构建前端格式的图片列表
    if result.get("success"):
        images = []

        # 🆕 提取 CSV 文件路径（用于原始数据展示）
        dispersion_csv_path = result.get("phonon_dispersion_csv")
        dos_csv_path = result.get("phonon_dos_csv")

        # 转换为前端可访问的 URL
        dispersion_csv_url = None
        dos_csv_url = None

        if dispersion_csv_path:
            csv_filename = Path(dispersion_csv_path).name
            dispersion_csv_url = f"{url_prefix}/{csv_filename}"
            logger.info(f"📊 Phonon dispersion CSV: {csv_filename} -> {dispersion_csv_url}")

        if dos_csv_path:
            csv_filename = Path(dos_csv_path).name
            dos_csv_url = f"{url_prefix}/{csv_filename}"
            logger.info(f"📊 Phonon DOS CSV: {csv_filename} -> {dos_csv_url}")

        # 处理声子色散图
        if result.get("phonon_band_plot_path") and result.get("phonon_band_plot_available"):
            band_path = Path(result["phonon_band_plot_path"])
            filename = band_path.name

            images.append({
                "name": "phonon_dispersion.png",
                "path": str(band_path),
                "type": "phonon_dispersion",
                "url": f"{url_prefix}/{filename}",
                "filename": filename,
                "available": True,
                # 🆕 添加 CSV 数据路径
                "dispersionCsvPath": dispersion_csv_url,
                "dosCsvPath": dos_csv_url
            })
            logger.info(f"📊 Phonon band plot: {filename} -> {url_prefix}/{filename}")

        # 处理声子态密度图
        if result.get("phonon_dos_plot_path") and result.get("phonon_dos_plot_available"):
            dos_path = Path(result["phonon_dos_plot_path"])
            filename = dos_path.name

            images.append({
                "name": "phonon_dos.png",
                "path": str(dos_path),
                "type": "phonon_dos",
                "url": f"{url_prefix}/{filename}",
                "filename": filename,
                "available": True,
                # 🆕 添加 CSV 数据路径
                "dispersionCsvPath": dispersion_csv_url,
                "dosCsvPath": dos_csv_url
            })
            logger.info(f"📊 Phonon DOS plot: {filename} -> {url_prefix}/{filename}")

        # 添加图片数据到结果中
        if images:
            result["images"] = images
            logger.info(f"✅ Phonon calculation completed with {len(images)} images")

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

        # Build upload directory path - use unified storage
        upload_dir = get_session_storage_path(
            session_id=session_id,
            data_type="cif",  # 使用 cif 类型，会映射到 session_data/simulation/{session_id}/cif/
            create=False
        )

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
    session_id: str,
    cif_path: str,
    method: str = "kappa_p",
    temperature: float = 300.0,
    keep_files: bool = False
) -> Dict[str, Any]:
    """
    Calculate thermal conductivity from a single CIF file.

    This tool calculates thermal conductivity for a SINGLE CIF file.
    For multiple files, use calculate_kappa_from_directory instead.

    ⚠️ 重要：session_id 是必需参数，用于隔离不同会话的计算结果。
    这确保了多个用户或多次计算不会相互覆盖文件。

    Args:
        session_id: Session ID (required) - identifies which session's calculation this belongs to
                   ⚠️ 必须提供，用于文件隔离和结果存储
        cif_path: Path to the CIF file (absolute or relative to project root)
        method: Calculation method - "kappa_p" or "kappa_mtp" (default: "kappa_p")
        temperature: Temperature in Kelvin (default: 300K)
        keep_files: Whether to keep generated CIF files for inspection

    Returns:
        Dict containing:
        - thermal_conductivity: {value, unit}
        - results_file: Path to CSV file with full calculation results
        - results_csv_url: URL to download the CSV file
        - key_metrics: Summary of key values (kappa, temperature, method, num_atoms)

    Examples:
        result = await calculate_kappa_from_cif(
            session_id="session_1234567890_abcdef",
            cif_path="session_data/simulation/session_1234567890_abcdef/cif/NaCl.cif",
            method="kappa_p"
        )
    """
    try:
        # Validate CIF file exists
        cif_file = Path(cif_path)
        if not cif_file.exists():
            return {
                "error": f"CIF file not found: {cif_path}",
                "timestamp": datetime.now().isoformat()
            }

        if not cif_file.suffix.lower() == '.cif':
            return {
                "error": f"File is not a CIF file: {cif_path}",
                "timestamp": datetime.now().isoformat()
            }

        # Read CIF content
        with open(cif_file, 'r', encoding='utf-8') as f:
            cif_content = f.read()

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
            cif_filename=cif_file.name,
            method=method,
            temperature=temperature,
            working_dir=str(working_dir_path) if working_dir_path else None,
            keep_files=keep_files,
            session_id=session_id
        )

        if keep_files and working_dir_path:
            result["working_directory"] = str(working_dir_path)

        return result

    except Exception as e:
        logger.error(f"Error calculating kappa from CIF: {e}")
        return {
            "error": f"Calculation failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@app.tool
async def calculate_kappa_from_directory(
    session_id: str,
    cif_directory: str,
    method: str = "kappa_p",
    temperature: float = 300.0,
    keep_files: bool = False
) -> Dict[str, Any]:
    """
    批量计算文件夹中所有 CIF 文件的热导率。

    ⚠️ 推荐：当有多个 CIF 文件需要计算热导率时，将它们放在同一文件夹中，使用此工具批量计算。

    ⚠️ 重要：session_id 是必需参数，用于隔离不同会话的计算结果。

    Args:
        session_id: Session ID (required) - identifies which session's calculation this belongs to
                   ⚠️ 必须提供，用于文件隔离和结果存储
        cif_directory: 包含 CIF 文件的文件夹路径（绝对路径或相对于项目根目录）
        method: 计算方法 - "kappa_p" 或 "kappa_mtp" (默认: "kappa_p")
        temperature: 温度（开尔文，默认: 300K)
        keep_files: 是否保留中间生成的 CIF 文件（默认: False）

    Returns:
        Dict 包含：
        - success: 是否成功
        - total: 总结构数
        - completed: 成功计算的数量
        - failed: 失败的数量
        - results: 每个结构的计算结果列表
        - summary: 结果摘要
        - batch_results_file: 批量结果 CSV 文件路径
        - batch_results_csv_url: 批量结果 CSV 文件的下载 URL

    Example:
        result = await calculate_kappa_from_directory(
            cif_directory="mcp_servers/simulation/cif/session_xxx/relax",
            method="kappa_p"
        )
    """
    try:
        # Validate directory exists
        cif_dir = Path(cif_directory)
        if not cif_dir.exists():
            return {
                "success": False,
                "error": f"Directory not found: {cif_directory}",
                "timestamp": datetime.now().isoformat()
            }

        if not cif_dir.is_dir():
            return {
                "success": False,
                "error": f"Path is not a directory: {cif_directory}",
                "timestamp": datetime.now().isoformat()
            }

        # Find all CIF files in directory
        cif_files = list(cif_dir.glob('*.cif')) + list(cif_dir.glob('*.CIF'))

        if not cif_files:
            return {
                "success": False,
                "error": f"No CIF files found in directory: {cif_directory}",
                "total": 0,
                "timestamp": datetime.now().isoformat()
            }

        logger.info(f"📁 Found {len(cif_files)} CIF files in {cif_directory}")

        # Build structures list from CIF files
        structures = []
        for cif_file in cif_files:
            try:
                with open(cif_file, 'r', encoding='utf-8') as f:
                    cif_content = f.read()

                # Extract formula from filename or CIF content
                formula = cif_file.stem

                structures.append({
                    "cifContent": cif_content,
                    "formula": formula,
                    "id": cif_file.stem,
                    "source_file": str(cif_file)
                })
            except Exception as e:
                logger.error(f"Error reading CIF file {cif_file}: {e}")
                continue

        if not structures:
            return {
                "success": False,
                "error": "Failed to read any CIF files from directory",
                "total": len(cif_files),
                "timestamp": datetime.now().isoformat()
            }

        # Use batch calculation
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
            keep_files=keep_files,
            session_id=session_id
        )

        if keep_files and working_dir_path:
            batch_result["working_directory"] = str(working_dir_path)

        return batch_result

    except Exception as e:
        logger.error(f"Error in batch calculation from directory: {e}")
        return {
            "success": False,
            "error": f"Batch calculation failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@app.tool
async def batch_calculate_kappa(
    session_id: str,
    structures: List[Dict[str, Any]],
    method: str = "kappa_p",
    temperature: float = 300.0,
    keep_files: bool = False
) -> Dict[str, Any]:
    """
    批量计算多个结构的热导率（从结构列表）。

    ⚠️ 注意：如果 CIF 文件已经保存在文件夹中，推荐使用 calculate_kappa_from_directory 工具。
    此工具适用于动态生成的结构数据。

    ⚠️ 重要：session_id 是必需参数，用于隔离不同会话的计算结果。

    Args:
        session_id: Session ID (required) - identifies which session's calculation this belongs to
                   ⚠️ 必须提供，用于文件隔离和结果存储
        structures: 结构列表，每个结构必须包含：
                   - cifContent 或 metadata.cifData: CIF 文件内容
                   - formula: 化学式（用于命名）
                   - id: 结构ID（可选）
        method: 计算方法 - "kappa_p" 或 "kappa_mtp" (默认: "kappa_p")
        temperature: 温度（开尔文，默认: 300K)
        keep_files: 是否保留中间生成的 CIF 文件（默认: False）

    Returns:
        Dict 包含：
        - success: 是否成功
        - total: 总结构数
        - completed: 成功计算的数量
        - failed: 失败的数量
        - results: 每个结构的计算结果列表
        - summary: 结果摘要
        - batch_results_csv_url: 批量结果 CSV 文件的下载 URL

    Example:
        structures = [
            {"cifContent": "...", "formula": "NaCl", "id": "struct1"},
            {"cifContent": "...", "formula": "GaN", "id": "struct2"}
        ]
        result = await batch_calculate_kappa(
            session_id="session_1234567890_abcdef",
            structures=structures,
            method="kappa_p"
        )
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
        keep_files=keep_files,
        session_id=session_id
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
    max_new_tokens: int = 2000,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate crystal structure from chemical composition using CrystaLLM.

    This tool uses the CrystaLLM AI model to generate realistic crystal structures
    from a given chemical composition. The generated structures are saved as CIF files
    and can be used for further calculations (energy, thermal conductivity, etc.).

    ⚠️ IMPORTANT: This tool returns FILE PATHS instead of full CIF content to optimize token consumption.
    Downstream tools (thermal conductivity, phonon spectrum) can read CIF files directly from these paths.

    Args:
        composition: Chemical composition (e.g., "Si", "GaN", "Fe2O3", "NaCl")
        device: Computing device ("cpu" or "cuda", default: "cuda")
        num_samples: Number of structures to generate (default: 1)
        top_k: Top-k sampling parameter for generation diversity (default: 10)
        max_new_tokens: Maximum tokens to generate (default: 2000)
        session_id: Session ID for unified storage (optional)

    Returns:
        Dict containing:
        - success: bool - Whether generation succeeded
        - cif_file_paths: List[str] - Paths to generated CIF files (optimized for token usage)
        - cif_filenames: List[str] - Generated CIF filenames
        - cif_directory: str - Directory containing all generated CIF files
        - composition: str - Input composition
        - generation_id: str - Unique generation ID
        - num_generated: int - Number of structures generated
        - frontend_structures: List[Dict] - Frontend-compatible structure data (includes cifContent for visualization)
        - error: str - Error message if failed

    Example:
        result = await generate_crystal_structure(composition="GaN", num_samples=3, session_id="session_123")
        if result["success"]:
            # Use file paths for downstream calculations
            for cif_path in result["cif_file_paths"]:
                # Read CIF when needed
                with open(cif_path, 'r') as f:
                    cif_content = f.read()
                # Or pass path directly to thermal conductivity calculation
                kappa_result = await calculate_kappa_from_cif(cif_content, ...)
    """
    result = generate_crystal_from_composition(
        composition=composition,
        device=device,
        num_samples=num_samples,
        top_k=top_k,
        max_new_tokens=max_new_tokens,
        session_id=session_id
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

        # Log file paths for verification
        if result.get("cif_file_paths"):
            logger.info(f"Generated CIF files saved to: {result.get('cif_directory')}")
            logger.info(f"File paths: {result['cif_file_paths']}")

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
