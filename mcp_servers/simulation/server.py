"""
Simulation MCP Server
Provides tools for computational simulation setup and analysis (VASP, Gaussian, LAMMPS).
Also provides MatterSim-based energy calculation, structure relaxation, and phonon calculation.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import os
from pathlib import Path
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
# 优先使用 VITE_API_URL（前端调用的API地址）
API_BASE_URL = os.getenv("VITE_API_URL")
if not API_BASE_URL:
    http_host = os.getenv("RESEARCHMIND_HTTP_HOST", "127.0.0.1")
    http_port = os.getenv("RESEARCHMIND_HTTP_PORT", "50002")
    # Use 127.0.0.1 if host is 0.0.0.0 (for local connections)
    if http_host == "0.0.0.0":
        http_host = "127.0.0.1"
    API_BASE_URL = f"http://{http_host}:{http_port}"
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

# Import file detection and CIF tools
from file_detector import detect_files_in_message_impl
from cif_tools import extract_and_validate_cif_impl, calculate_kappa_from_cif_impl

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
        # 确保 API_BASE_URL 没有尾部斜杠
        base_url = API_BASE_URL.rstrip('/')

        if SESSION_MANAGER_AVAILABLE and session_id:
            # 使用会话目录
            phonon_dir = SessionManager.get_session_phonon_dir(session_id)
            url_prefix = f"{base_url}/api/images/{session_id}/phonon_results"
            logger.info(f"📁 Using session phonon directory: {phonon_dir}")
        else:
            # 使用全局目录（向后兼容）
            phonon_dir = Path(__file__).parent / "phonon_results"
            url_prefix = f"{base_url}/api/images/phonon_results"
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


# File Detection and CIF Tools
@app.tool
async def detect_file_upload(
    message_parts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Detect if user has uploaded any files.

    **IMPORTANT**: This tool should be called FIRST when receiving ANY user message,
    even if the message appears to be empty or contains only text.

    This tool will:
    - Detect all uploaded files
    - Identify CIF files specifically
    - Provide file information (name, size, type)
    - Return a summary of detected files

    Args:
        message_parts: List of message parts from user message
                      Expected structure: [{"resource": {"name": "...", "blob": {"data": "..."}}}]

    Returns:
        Dict containing:
        - has_files: bool - Whether any files were detected
        - file_count: int - Number of files detected
        - files: List[Dict] - Information about each file
        - cif_files: List[Dict] - CIF files specifically
        - other_files: List[Dict] - Non-CIF files
        - summary: str - Human-readable summary
    """
    return detect_files_in_message_impl(message_parts=message_parts)


@app.tool
async def debug_message_parts(
    message_parts: Any
) -> Dict[str, Any]:
    """
    Debug tool to inspect the structure of message_parts.

    This tool helps diagnose issues with file detection by showing
    the actual structure of the data being passed.

    Args:
        message_parts: Any data to inspect

    Returns:
        Dict containing detailed structure information
    """
    try:
        result = {
            "type": type(message_parts).__name__,
            "is_list": isinstance(message_parts, list),
            "is_dict": isinstance(message_parts, dict),
            "is_none": message_parts is None,
            "is_string": isinstance(message_parts, str),
            "repr": str(message_parts)[:500],  # First 500 chars
        }

        if hasattr(message_parts, '__len__'):
            result["length"] = len(message_parts)
        else:
            result["length"] = "N/A"

        if isinstance(message_parts, dict):
            result["keys"] = list(message_parts.keys())

        if isinstance(message_parts, list) and len(message_parts) > 0:
            result["first_item_type"] = type(message_parts[0]).__name__
            result["first_item_repr"] = str(message_parts[0])[:200]
            if isinstance(message_parts[0], dict):
                result["first_item_keys"] = list(message_parts[0].keys())

        return result

    except Exception as e:
        return {
            "error": str(e),
            "type": type(message_parts).__name__
        }


@app.tool
async def extract_and_validate_cif(
    message_parts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Extract CIF file from user message and validate its content.

    This tool extracts CIF files from uploaded message parts and validates
    that the content is a valid CIF file format.

    Args:
        message_parts: List of message parts from user message
                      Expected structure: [{"resource": {"name": "...", "blob": {"data": "..."}}}]

    Returns:
        Dict containing:
        - success: bool - Whether extraction and validation succeeded
        - cif_content: str - Extracted CIF content (decoded if base64)
        - cif_filename: str - Original filename
        - is_valid: bool - Whether CIF format is valid
        - validation_details: Dict - Details about validation
        - error: str - Error message if failed
    """
    return extract_and_validate_cif_impl(message_parts=message_parts)


@app.tool
async def calculate_kappa_from_cif(
    cif_content,  # Can be str or List[Dict]
    cif_filename: str = "material.cif",
    method: str = "kappa_p",
    temperature: float = 300.0
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
    return calculate_kappa_from_cif_impl(
        cif_content=cif_content,
        cif_filename=cif_filename,
        method=method,
        temperature=temperature
    )


@app.tool
async def batch_calculate_kappa(
    structures: List[Dict[str, Any]],
    method: str = "kappa_p",
    temperature: float = 300.0
) -> Dict[str, Any]:
    """
    批量计算多个结构的热导率 - 这是处理多个结构的主要工具
    
    ⚠️ 重要：当有多个结构需要计算热导率时，必须使用此工具而不是多次调用单个计算工具
    
    Args:
        structures: 结构列表，每个结构必须包含：
                   - cifContent 或 metadata.cifData: CIF 文件内容
                   - formula: 化学式（用于命名）
                   - id: 结构ID（可选）
        method: 计算方法 - "kappa_p" 或 "kappa_mtp" (默认: "kappa_p")
        temperature: 温度（开尔文）(默认: 300K)
    
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
    import asyncio
    
    logger.info(f"🔄 Starting batch thermal conductivity calculation for {len(structures)} structures")
    
    results = []
    completed = 0
    failed = 0
    
    for i, structure in enumerate(structures):
        structure_id = structure.get("id", f"structure_{i+1}")
        formula = structure.get("formula", f"Unknown_{i+1}")
        
        # 获取 CIF 内容（统一使用 cifContent 字段）
        cif_content = structure.get("cifContent")
        
        if not cif_content:
            logger.warning(f"WARNING: Structure {i+1} ({formula}) has no CIF content, skipping")
            results.append({
                "structure_id": structure_id,
                "formula": formula,
                "success": False,
                "error": "No CIF content available"
            })
            failed += 1
            continue
        
        try:
            logger.info(f"📊 Calculating thermal conductivity for structure {i+1}/{len(structures)}: {formula}")
            
            # 调用单个计算函数
            result = calculate_kappa_from_cif_impl(
                cif_content=cif_content,
                cif_filename=f"{formula}_{structure_id}.cif",
                method=method,
                temperature=temperature
            )
            
            # 添加结构信息到结果
            result["structure_id"] = structure_id
            result["formula"] = formula
            result["index"] = i + 1
            
            if result.get("success", False):
                completed += 1
                logger.info(f"Structure {i+1} ({formula}): kappa = {result.get('kappa_total', 'N/A')} W/mK")
            else:
                failed += 1
                logger.warning(f"ERROR: Structure {i+1} ({formula}) calculation failed: {result.get('error', 'Unknown error')}")
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"ERROR: Error calculating structure {i+1} ({formula}): {e}")
            results.append({
                "structure_id": structure_id,
                "formula": formula,
                "index": i + 1,
                "success": False,
                "error": str(e)
            })
            failed += 1
    
    # 生成摘要
    summary = {
        "total_structures": len(structures),
        "completed": completed,
        "failed": failed,
        "success_rate": f"{(completed/len(structures)*100):.1f}%" if structures else "0%",
        "method": method,
        "temperature": temperature
    }
    
    # 提取成功的热导率值
    successful_kappas = [
        {
            "formula": r["formula"],
            "kappa_total": r.get("kappa_total"),
            "kappa_xx": r.get("kappa_xx"),
            "kappa_yy": r.get("kappa_yy"),
            "kappa_zz": r.get("kappa_zz")
        }
        for r in results if r.get("success", False) and r.get("kappa_total") is not None
    ]
    
    if successful_kappas:
        summary["thermal_conductivities"] = successful_kappas
        # 计算平均值
        avg_kappa = sum(k["kappa_total"] for k in successful_kappas) / len(successful_kappas)
        summary["average_kappa"] = round(avg_kappa, 4)
    
    logger.info(f"Batch calculation completed: {completed}/{len(structures)} successful")
    
    return {
        "success": True,
        "total": len(structures),
        "completed": completed,
        "failed": failed,
        "results": results,
        "summary": summary
    }


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
