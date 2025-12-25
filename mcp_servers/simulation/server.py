"""
Simulation MCP Server
Provides tools for computational simulation setup and analysis.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import sys
import os
import re
import shutil
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from fastmcp import FastMCP
import structlog

# Setup paths
current_dir = Path(__file__).resolve().parent
# current_dir is .../mcp_servers/simulation
# parent is .../mcp_servers
# parent.parent is .../ResearchMind
root_dir = current_dir.parent.parent
services_path = root_dir / "services"
shared_path = root_dir / "shared"
mcp_shared_path = root_dir / "mcp_servers" / "shared"
modules_path = current_dir / "modules"
crystallm_path = current_dir / "crystallm"

for path in [services_path, shared_path, mcp_shared_path, modules_path, crystallm_path, current_dir]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Load environment variables
env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Windows encoding fix
if os.name == 'nt':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

logger = structlog.get_logger(__name__)

# Import core modules
from storage_manager import get_session_storage_path
from cif_tools import calculate_kappa_from_cif_impl
from generator import generate_crystal_from_composition

# Optional imports
try:
    from kappa_lib import is_kappa_available
    KAPPA_AVAILABLE = is_kappa_available()
except ImportError:
    KAPPA_AVAILABLE = False
    is_kappa_available = lambda: False

MATTERSIM_AVAILABLE = False
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
except ImportError:
    pass

try:
    from session_manager import SessionManager
    SESSION_MANAGER_AVAILABLE = True
except ImportError:
    SESSION_MANAGER_AVAILABLE = False



def _build_kappa_working_dir(session_id: str, prefix: str = "kappa") -> Optional[Path]:
    """
    Create a temporary working directory for kappa calculations.
    """
    try:
        if session_id:
            base_dir = get_session_storage_path(session_id, "temp", create=True)
            return Path(tempfile.mkdtemp(prefix=f"{prefix}_", dir=base_dir))
    except Exception as e:
        logger.error(f"Failed to create working directory: {e}")
    return None


def _resolve_structure_path_by_source(session_id: str, filename: str, source: str) -> Optional[Path]:
    """
    Resolve structure file path from unified storage based on source.
    """
    # 🆕 Allow using full path if provided and exists (fixes frontend path mismatch)
    try:
        if filename:
            p = Path(filename)
            # Check if it's an absolute path or exists relative to CWD
            if p.is_absolute() or p.exists():
                if p.exists() and p.is_file():
                    logger.info(f"Using provided path for structure: {p}")
                    return p
    except Exception:
        pass

    # Security: Ensure filename is just a name, not a path
    filename = Path(filename).name
    
    source_lower = str(source).lower()
    priority = []
    
    if source_lower in ["upload", "uploaded", "uploads"]:
        priority = ["uploads", "cif"]
    elif source_lower in ["relax", "relaxed", "relaxed_structures"]:
        priority = ["relaxed_structures"]
    elif source_lower in ["generate", "generated", "generated_structures"]:
        priority = ["generated_structures"]
    elif source_lower in ["database", "db", "mp", "oqmd", "cod", "aflow"]:
        # 🆕 数据库检索的结构
        priority = ["database"]
    
    # Add fallbacks (包含 database 目录)
    search_order = priority + [t for t in ["relaxed_structures", "database", "cif", "uploads", "generated_structures"] if t not in priority]
    
    for data_type in search_order:
        try:
            storage_path = get_session_storage_path(session_id, data_type, create=False)
            if not storage_path.exists(): continue
            
            # 1. Exact match (Direct check)
            if (f := storage_path / filename).exists(): return f
            
            # 2. Fuzzy match (prefix/suffix/containment)
            # Useful when requested "NaCl.cif" but stored as "MP_NaCl_123.cif"
            filename_stem = Path(filename).stem
            filename_suffix = Path(filename).suffix
            
            # List all files in directory
            candidates = list(storage_path.glob(f"*{filename_suffix}")) if filename_suffix else list(storage_path.glob("*"))
            
            for candidate in candidates:
                # Check if the requested stem is part of the candidate name
                # e.g. "NaCl" in "MP_NaCl_3735_2025..."
                if filename_stem in candidate.name:
                    logger.info(f"Using fuzzy match for structure: {filename} -> {candidate.name}")
                    return candidate

            # 3. Recursive check for generated structures (already covered by fuzzy if flat, but keeping for nested)
            if data_type == "generated_structures":
                 if found := list(storage_path.rglob(filename)): return found[0]
        except Exception:
            continue

    return None


def _resolve_structures(session_id: str, structures: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Helper to resolve and read multiple structures.
    Supports multiple input formats:
    1. cif_file_path: Direct absolute path to CIF file (from database queries)
    2. filename + source: Resolve path based on session storage
    3. cifContent: Direct CIF content (no file needed)
    
    Returns (resolved_list, missing_filenames_list)
    """
    resolved = []
    missing = []
    for i, struct in enumerate(structures, 1):
        # 🆕 Priority 1: Check for direct cif_file_path (from database queries)
        cif_file_path = struct.get("cif_file_path") or struct.get("path")
        if cif_file_path:
            cif_path = Path(cif_file_path)
            if cif_path.exists() and cif_path.is_file():
                try:
                    content = cif_path.read_text(encoding='utf-8')
                    resolved.append({
                        "filename": cif_path.name,
                        "path": cif_path,
                        "content": content,
                        "source": struct.get("source", "database")
                    })
                    logger.info(f"✅ Resolved structure {i} from cif_file_path: {cif_path}")
                    continue
                except Exception as e:
                    logger.error(f"❌ Error reading cif_file_path {cif_file_path}: {e}")
        
        # 🆕 Priority 2: Check for direct cifContent (no file resolution needed)
        cif_content = struct.get("cifContent") or struct.get("cif_content")
        if cif_content and cif_content != "N/A":
            filename = struct.get("filename") or struct.get("name") or struct.get("formula_pretty") or f"structure_{i}"
            resolved.append({
                "filename": filename,
                "path": None,  # No file path, content provided directly
                "content": cif_content,
                "source": struct.get("source", "inline")
            })
            logger.info(f"✅ Resolved structure {i} from inline cifContent: {filename}")
            continue
        
        # Priority 3: Resolve by filename and source
        filename = struct.get("filename") or struct.get("name")
        source = struct.get("source", "upload")
        
        if not filename:
            logger.warning(f"⚠️ Structure {i} missing filename and no cif_file_path/cifContent, skipping.")
            continue
            
        cif_path = _resolve_structure_path_by_source(session_id, filename, source)
        if cif_path and cif_path.exists():
            try:
                content = cif_path.read_text(encoding='utf-8')
                resolved.append({
                    "filename": filename,
                    "path": cif_path,
                    "content": content,
                    "source": source
                })
                logger.info(f"✅ Resolved structure {i} from session storage: {cif_path}")
            except Exception as e:
                logger.error(f"❌ Error reading {filename}: {e}")
                missing.append(filename)
        else:
            logger.warning(f"⚠️ File not found: {filename} (source: {source}, session: {session_id})")
            missing.append(filename)
            
    return resolved, missing


# Create FastMCP app
app = FastMCP("simulation")

# Cache for generated structures keyed by session_id
generated_structures_cache: Dict[str, List[Any]] = {}


@app.tool
async def calculate_phonon(
    session_id: str,
    structures: List[Dict[str, Any]],
    perform_relaxation: bool = True,
    device: str = "cpu",
    supercell_matrix: Optional[List[int]] = None,
    amplitude: float = 0.01,
    find_prim: bool = True,
    keep_intermediate_files: bool = False
) -> Dict[str, Any]:
    """
    Calculate phonon spectra for selected structures (single or batch).
    """
    if not MATTERSIM_AVAILABLE:
        return {"success": False, "error": "MatterSim not available."}

    resolved, missing = _resolve_structures(session_id, structures)
    
    results = []
    failed = len(missing)
    for m in missing:
        results.append({"filename": m, "success": False, "error": "File not found or unreadable"})

    if not resolved and not missing:
        return {"success": False, "error": "No valid structures found."}

    logger.info(f"📊 Selected {len(resolved)} structures for phonon calculation")

    work_dir = None
    try:
        # Create temp dir
        if session_id:
            base_temp_dir = get_session_storage_path(session_id=session_id, data_type="temp", create=True)
            work_dir = Path(tempfile.mkdtemp(prefix="batch_phonon_", dir=base_temp_dir))
        else:
            work_dir = Path(tempfile.mkdtemp(prefix="batch_phonon_"))
        
        ready_files = []
        
        # Prepare files
        for r in resolved:
            dest_path = work_dir / r["filename"]
            dest_path.write_text(r["content"], encoding='utf-8')
            
            if perform_relaxation:
                try:
                    logger.info(f"  ⚡ Relaxing: {r['filename']}")
                    relax_result = relax_structure_impl(
                        cif_content=r["content"],
                        cif_filename=r["filename"],
                        device=device,
                        optimizer="BFGS",
                        filter_type="ExpCellFilter",
                        constrain_symmetry=True,
                        max_steps=500,
                        fmax=0.01
                    )
                    
                    # 🆕 Auto-retry logic for symmetry constraint failures
                    if not relax_result.get("success"):
                        error_msg = relax_result.get("error", "")
                        if "deformation gradient" in error_msg or "symmetry" in error_msg:
                            logger.info(f"  ⚠️ Symmetry constraint failed for {r['filename']}, retrying without constraints...")
                            relax_result = relax_structure_impl(
                                cif_content=r["content"],
                                cif_filename=r["filename"],
                                device=device,
                                optimizer="BFGS",
                                filter_type="ExpCellFilter",
                                constrain_symmetry=False,
                                max_steps=500,
                                fmax=0.01
                            )
                    
                    if relax_result.get("success"):
                        relaxed_name = f"relaxed_{r['filename']}"
                        relaxed_path = work_dir / relaxed_name
                        relaxed_path.write_text(relax_result["relaxed_cif_content"], encoding='utf-8')
                        ready_files.append(relaxed_path)
                    else:
                        logger.warning(f"  ❌ Relaxation failed for {r['filename']}")
                        failed += 1
                        results.append({"filename": r['filename'], "success": False, "error": f"Relaxation failed: {relax_result.get('error')}"})
                except Exception as e:
                    logger.error(f"  ❌ Error relaxing {r['filename']}: {e}")
                    failed += 1
                    results.append({"filename": r['filename'], "success": False, "error": f"Relaxation error: {str(e)}"})
            else:
                ready_files.append(dest_path)

        if not ready_files and not results:
             return {"success": False, "error": "No valid structures prepared."}

        # Calculate
        logger.info(f"🔄 Starting phonon calculation for {len(ready_files)} structures...")
        # results list already contains missing/failed-relaxation items
        completed = 0
        all_images = []
        
        phonon_dir = get_session_storage_path(session_id, "phonon_results", create=True)

        for i, cif_file in enumerate(ready_files, 1):
            try:
                result = calculate_phonon_impl(
                    cif_content=cif_file.read_text(encoding='utf-8'),
                    cif_filename=cif_file.name,
                    device=device,
                    supercell_matrix=supercell_matrix or [2, 2, 2],
                    amplitude=amplitude,
                    find_prim=find_prim,
                    output_dir=str(phonon_dir)
                )

                if result.get("success"):
                    completed += 1
                    # Process images (simplified)
                    url_prefix = f"/api/images/phonon/{session_id}/phonon_results/{result.get('structure_directory')}"
                    
                    for plot_type, name_suffix in [("phonon_band_plot_path", "Dispersion"), ("phonon_dos_plot_path", "DOS")]:
                        if path := result.get(plot_type):
                            p = Path(path)
                            if p.exists():
                                all_images.append({
                                    "name": f"{cif_file.stem} - Phonon {name_suffix}",
                                    "url": f"{url_prefix}/{p.name}",
                                    "type": f"phonon_{name_suffix.lower()}",
                                    "available": True
                                })
                else:
                    failed += 1
                
                results.append({"filename": cif_file.name, **result})

            except Exception as e:
                failed += 1
                results.append({"filename": cif_file.name, "success": False, "error": str(e)})

        # Cleanup
        if not keep_intermediate_files and work_dir.exists():
            shutil.rmtree(work_dir)

        return {
            "success": completed > 0,
            "total": len(structures),
            "completed": completed,
            "failed": failed,
            "results": results,
            "images": all_images
        }

    except Exception as e:
        if work_dir and work_dir.exists():
            shutil.rmtree(work_dir)
        return {"success": False, "error": str(e)}


# Health check will be handled by the HTTP server when running with uvicorn










# MatterSim-based tools
@app.tool
async def calculate_energy(
    session_id: str,
    structures: List[Dict[str, Any]],
    device: str = "cuda"
) -> Dict[str, Any]:
    """
    Calculate energy properties for selected structures (single or batch) using MatterSim.
    """
    if not MATTERSIM_AVAILABLE:
        return {"success": False, "error": "MatterSim not available."}

    resolved, missing = _resolve_structures(session_id, structures)
    
    results = []
    failed = len(missing)
    for m in missing:
        results.append({"filename": m, "success": False, "error": "File not found or unreadable"})

    if not resolved and not missing:
        return {"success": False, "error": "No valid structures found."}

    logger.info(f"🔄 Starting energy calculation for {len(resolved)} structures")

    completed = 0

    for i, r in enumerate(resolved, 1):
        try:
            logger.info(f"  ⚡ Calculating energy {i}/{len(resolved)}: {r['filename']}")
            result = calculate_energy_from_cif_impl(r["content"], r["filename"], device)
            
            if result.get("success"):
                completed += 1
                result["filename"] = r["filename"]
            else:
                failed += 1
                logger.warning(f"  ❌ Energy calculation failed for {r['filename']}: {result.get('error')}")

            results.append(result)

        except Exception as e:
            failed += 1
            logger.error(f"❌ Error calculating energy for {r['filename']}: {e}")
            results.append({"success": False, "error": str(e), "filename": r["filename"]})

    return {
        "success": completed > 0,
        "total": len(structures),
        "completed": completed,
        "failed": failed,
        "results": results,
        "summary": {
            "total_structures": len(structures),
            "successful": completed,
            "failed": failed
        }
    }


@app.tool
async def relax_structure(
    session_id: str,
    structures: List[Dict[str, Any]],
    device: str = "cuda",
    optimizer: str = "BFGS",
    filter_type: str = "ExpCellFilter",
    constrain_symmetry: bool = True,
    max_steps: int = 500,
    fmax: float = 0.01
) -> Dict[str, Any]:
    """
    Perform structure relaxation for selected structures (single or batch).
    """
    if not MATTERSIM_AVAILABLE:
        return {"success": False, "error": "MatterSim not available."}

    resolved, missing = _resolve_structures(session_id, structures)
    
    results = []
    failed = len(missing)
    for m in missing:
        results.append({"filename": m, "success": False, "error": "File not found or unreadable"})

    if not resolved and not missing:
        return {"success": False, "error": "No valid structures found."}

    logger.info(f"🔄 Starting relaxation for {len(resolved)} structures")

    # Import here to avoid circular imports, but outside loop
    try:
        from modules.cif_tools import convert_cif_to_frontend_structure
    except ImportError:
        convert_cif_to_frontend_structure = None

    completed = 0

    for i, r in enumerate(resolved, 1):
        try:
            logger.info(f"  ⚡ Relaxing {i}/{len(resolved)}: {r['filename']}")

            result = relax_structure_impl(
                r["content"], r["filename"], device, optimizer, filter_type,
                constrain_symmetry, max_steps, fmax
            )

            # 🆕 Auto-retry logic for symmetry constraint failures
            if not result.get("success") and constrain_symmetry:
                error_msg = result.get("error", "")
                if "deformation gradient" in error_msg or "symmetry" in error_msg:
                    logger.info(f"  ⚠️ Symmetry constraint failed for {r['filename']}, retrying without constraints...")
                    result = relax_structure_impl(
                        r["content"], r["filename"], device, optimizer, filter_type,
                        False, max_steps, fmax  # Retry with constrain_symmetry=False
                    )

            if result.get("success") and result.get("relaxed_cif_content"):
                # Save relaxed structure
                structures_dir = get_session_storage_path(session_id, "relaxed_structures", create=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = Path(r["filename"]).stem
                relaxed_filename = f"relaxed_{base_name}_{timestamp}.cif"
                relaxed_file_path = structures_dir / relaxed_filename

                relaxed_file_path.write_text(result["relaxed_cif_content"], encoding='utf-8')

                # Update result
                result["relaxed_cif_file"] = str(relaxed_file_path)
                result["relaxed_cif_filename"] = relaxed_filename
                result["source_file"] = r["filename"]
                
                # Convert to frontend format
                if convert_cif_to_frontend_structure:
                    frontend_structure = convert_cif_to_frontend_structure(
                        result["relaxed_cif_content"],
                        result.get("composition", "Unknown"),
                        source="Relaxed"
                    )
                    
                    if frontend_structure:
                        frontend_structure["source"] = {"database": "Relaxed", "isRelaxed": True}
                        frontend_structure["cifFilename"] = relaxed_filename  # 🆕 添加文件名引用
                        frontend_structure["cif_file_path"] = str(relaxed_file_path)  # 🆕 添加完整文件路径
                        frontend_structure["metadata"] = {
                            "relaxation": {
                                "initial_energy": result.get("initial_energy"),
                                "final_energy": result.get("final_energy"),
                                "energy_change": result.get("energy_change")
                            },
                            "source_file": r["filename"]  # 原始文件名
                        }
                        result["frontend_structure"] = frontend_structure

                if "relaxed_cif_content" in result:
                    del result["relaxed_cif_content"]
                
                completed += 1
            else:
                failed += 1
                logger.warning(f"  ❌ Relaxation failed for {r['filename']}: {result.get('error')}")

            results.append(result)

        except Exception as e:
            failed += 1
            logger.error(f"❌ Error relaxing {r['filename']}: {e}")
            results.append({"success": False, "error": str(e), "filename": r["filename"]})

    # 🆕 提取所有成功的 frontend_structure 到顶层，便于前端处理
    frontend_structures = [r["frontend_structure"] for r in results if r.get("success") and r.get("frontend_structure")]

    return {
        "success": completed > 0,
        "total": len(structures),
        "completed": completed,
        "failed": failed,
        "results": results,
        "frontend_structures": frontend_structures,  # 🆕 添加顶层结构列表
        "summary": {
            "total_structures": len(structures),
            "successful": completed,
            "failed": failed
        }
    }





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
        "version": "2.1.0",
        "available_tools": [
            "calculate_energy",
            "relax_structure",
            "calculate_phonon",
            "calculate_kappa",
            "generate_crystal_structure",
            "extract_and_validate_cif",
            "get_latest_generated_structures",
            "clear_structure_cache"
        ],
        "supported_software": ["MatterSim", "CrystaLLM", "KappaLib"],
        "mattersim_available": MATTERSIM_AVAILABLE,
        "kappa_available": KAPPA_AVAILABLE,
        "session_manager_available": SESSION_MANAGER_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }


def _standardize_cif(cif_content: str) -> str:
    """
    Standardize CIF content using pymatgen and clean up for ASE compatibility.
    """
    try:
        from pymatgen.io.cif import CifParser, CifWriter
        from io import StringIO

        parser = CifParser(StringIO(cif_content))
        structure = parser.get_structures()[0]
        writer = CifWriter(structure, symprec=0.01)
        standardized = str(writer)

        # Clean up lines
        cleaned_lines = []
        for line in standardized.split('\n'):
            sline = line.strip()
            if sline.startswith(('_symmetry_Int_Tables_number', '_space_group_IT_number')):
                continue
            if sline.startswith('_symmetry_space_group_name_H-M'):
                line = line.replace('_1', '1').replace('_2', '2').replace('_3', '3').replace('_4', '4').replace('_6', '6')
            cleaned_lines.append(line)
            
        return '\n'.join(cleaned_lines)
    except Exception as e:
        logger.warning(f"⚠️ CIF standardization failed: {e}")
        return cif_content


@app.tool
async def extract_and_validate_cif(
    session_id: str,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract and validate CIF file from uploaded files.
    """
    try:
        from modules.cif_tools import convert_cif_to_frontend_structure
        
        # Check both cif and uploads directories
        search_dirs = []
        cif_dir = get_session_storage_path(session_id, "cif", create=False)
        uploads_dir = get_session_storage_path(session_id, "uploads", create=False)
        
        if cif_dir.exists(): search_dirs.append(cif_dir)
        if uploads_dir.exists(): search_dirs.append(uploads_dir)
        
        if not search_dirs:
            return {"success": False, "error": "No CIF or uploads directories found.", "is_valid": False}

        cif_files = []
        found_file = None
        
        if filename:
            # Try to resolve absolute path first (from agent prompt)
            fname_path = Path(filename)
            if fname_path.is_absolute() and fname_path.exists():
                cif_files = [fname_path]
            else:
                target_name = fname_path.name
                
                # Check all directories
                for d in search_dirs:
                    exact = d / target_name
                    if exact.exists():
                        cif_files = [exact]
                        break
                    
                    # Fuzzy search
                    base, suffix = Path(target_name).stem, Path(target_name).suffix
                    candidates = sorted(d.glob(f"*{base}*{suffix}"), key=lambda x: x.name, reverse=True)
                    if candidates:
                        cif_files = candidates
                        break
                
                if not cif_files:
                    return {"success": False, "error": f"File {filename} not found in {search_dirs}", "is_valid": False}
        else:
            # List all CIFs in all dirs
            for d in search_dirs:
                cif_files.extend(list(d.glob("*.cif")))
            
            if not cif_files:
                return {"success": False, "error": "No CIF files in upload directories.", "is_valid": False}

        cif_file = cif_files[0]
        cif_content = cif_file.read_text(encoding='utf-8')
        
        # Standardize
        standardized_cif = _standardize_cif(cif_content)
        if standardized_cif != cif_content:
            cif_file.write_text(standardized_cif, encoding='utf-8')
            cif_content = standardized_cif

        # Validate
        result = _validate_cif_content(cif_content, cif_file.name)
        result.update({
            "file_path": str(cif_file),
            "session_id": session_id,
            "saved_filename": cif_file.name,
            "original_filename": filename or cif_file.name
        })
        
        # 🆕 Convert to frontend structure
        frontend_structure = convert_cif_to_frontend_structure(
            cif_content=cif_content,
            composition=result.get("composition", "Unknown"),
            source="Upload"
        )
        
        if frontend_structure:
            frontend_structure["source"] = {"database": "Upload", "isUploaded": True}
            frontend_structure["cifFilename"] = cif_file.name
            frontend_structure["cif_file_path"] = str(cif_file)  # 🆕 Critical: Provide absolute path
            frontend_structure["metadata"] = {
                "source_file": str(cif_file),
                "is_valid": result.get("is_valid", False)
            }
            result["frontend_structure"] = frontend_structure
        
        return result

    except Exception as e:
        logger.error(f"❌ Error extracting CIF: {e}")
        return {"success": False, "error": str(e), "is_valid": False}


def _validate_cif_content(cif_content: str, filename: str) -> Dict[str, Any]:
    """
    Perform minimal validation of CIF file content.
    """
    try:
        if not cif_content or not cif_content.strip():
            return {"success": False, "cif_filename": filename, "is_valid": False, "error": "Empty CIF file"}

        if not cif_content.isprintable() and not any(c in cif_content for c in ['\n', '\r', '\t']):
            return {"success": False, "cif_filename": filename, "is_valid": False, "error": "Binary file detected"}

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
        except Exception:
            pass

        result = {
            "success": True,
            "cif_filename": filename,
            "is_valid": True,
            "file_size_kb": round(len(cif_content) / 1024, 2),
            "message": f"✅ CIF loaded ({round(len(cif_content) / 1024, 2)} KB)"
        }

        if structure_info:
            result["structure_info"] = structure_info
            result["message"] += f" - {structure_info['formula']}, {structure_info['num_atoms']} atoms"

        return result

    except Exception as e:
        logger.error(f"❌ Error validating CIF: {e}")
        return {"success": False, "cif_filename": filename, "is_valid": False, "error": str(e)}





@app.tool
async def calculate_kappa(
    session_id: str,
    structures: List[Dict[str, Any]],
    method: str = "kappa_p",
    temperature: float = 300.0,
    keep_files: bool = False
) -> Dict[str, Any]:
    """
    Calculate thermal conductivity for selected structures (single or batch).
    
    Args:
        session_id: Session ID.
        structures: List of structures to process. Each item should be a dict with:
                    - "filename": The CIF filename.
                    - "source": The source of the file ("upload", "relax", "generate").
        method: Calculation method ("kappa_p" or "kappa_mtp").
        temperature: Temperature in Kelvin.
        keep_files: Whether to keep intermediate files.
    """
    logger.info(
        "🔄 Starting thermal conductivity calculation",
        structures=len(structures),
        method=method,
        temperature=temperature,
        session_id=session_id
    )

    # 1. Resolve paths and read content for all structures
    resolved_structures = []
    for i, struct in enumerate(structures, 1):
        filename = struct.get("filename") or struct.get("name")
        source = struct.get("source", "upload")
        
        if not filename:
            logger.warning(f"⚠️ Structure {i} missing filename, skipping.")
            continue
            
        cif_path = _resolve_structure_path_by_source(session_id, filename, source)
        if not cif_path or not cif_path.exists():
            logger.warning(f"⚠️ File not found: {filename} (source: {source}), skipping.")
            continue
            
        try:
            cif_content = cif_path.read_text(encoding='utf-8')
            resolved_structures.append({
                "cifContent": cif_content,
                "formula": cif_path.stem, # Use stem as formula/ID
                "id": cif_path.stem,
                "source_file": str(cif_path)
            })
        except Exception as e:
            logger.error(f"❌ Error reading {filename}: {e}")

    if not resolved_structures:
        return {"success": False, "error": "No valid structures found."}

    # 2. Prepare working directory
    working_dir_path = _build_kappa_working_dir(session_id, prefix="batch")
    if working_dir_path:
        logger.info(
            "Using session-scoped batch working directory",
            session_id=session_id,
            working_dir=str(working_dir_path)
        )
    elif session_id and SESSION_MANAGER_AVAILABLE:
        logger.warning("Session ID provided but failed to build batch working directory", session_id=session_id)

    # 3. Call implementation
    batch_result = calculate_kappa_from_cif_impl(
        cif_content=resolved_structures,
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
            "total": batch_result.get("total", len(resolved_structures)),
            "completed": batch_result.get("completed", 0),
            "failed": batch_result.get("failed", 0),
            "results": batch_result.get("results", []),
            "summary": batch_result.get("summary", {}),
            "timestamp": batch_result.get("timestamp", datetime.now().isoformat()),
            # 🆕 Pass through CSV URLs and paths for frontend display
            "batch_results_csv_url": batch_result.get("batch_results_csv_url"),
            "results_csv_url": batch_result.get("results_csv_url"),
            "batch_results_file": batch_result.get("batch_results_file"),
            "results_file": batch_result.get("results_file")
        }
        if keep_files and working_dir_path:
            response["working_directory"] = str(working_dir_path)
        return response

    return batch_result


@app.tool
async def generate_crystal_structure(
    composition: str,
    session_id: str,
    device: str = "cuda",
    num_samples: int = 1,
    top_k: int = 10,
    max_new_tokens: int = 2000,
    spacegroup: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate crystal structure from chemical composition using CrystaLLM.
    """
    result = generate_crystal_from_composition(
        composition=composition,
        device=device,
        num_samples=num_samples,
        top_k=top_k,
        max_new_tokens=max_new_tokens,
        session_id=session_id,
        spacegroup=spacegroup
    )

    if result.get("success") and result.get("frontend_structures"):
        generated_structures_cache[session_id] = result["frontend_structures"]
        result["structures"] = result["frontend_structures"]
        logger.info(f"Cached {len(result['frontend_structures'])} structures for {composition} (session: {session_id})")

    return result

# 🗑️ get_latest_generated_structures 已删除 - 该工具返回的结构缺少正确的 source 信息，导致显示 "Unknown"


@app.tool 
async def clear_structure_cache(session_id: str) -> Dict[str, Any]:
    """
    Clear structure cache for the session.
    """
    count = 0
    if session_id in generated_structures_cache:
        count = len(generated_structures_cache[session_id])
        del generated_structures_cache[session_id]
    return {"success": True, "message": f"Cleared {count} structures for session {session_id}"}


if __name__ == "__main__":
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
