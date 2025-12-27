"""
MatterSim Energy Prediction Module

Calculates formation energy, decomposition energy, energy per atom, forces,
performs structure relaxation, and computes phonon spectra
using MatterSim official package and pretrained models.

Based on MatterSim official usage:
https://github.com/microsoft/mattersim
https://microsoft.github.io/mattersim/user_guide/getting_started.html
https://microsoft.github.io/mattersim/examples/relax_example.html
https://microsoft.github.io/mattersim/examples/phonon_example.html
"""

import base64
import tempfile
import shutil
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import uuid
import numpy as np

import structlog
import torch
from ase import io as ase_io
from ase.units import GPa
from ase.optimize import BFGS
from ase.constraints import FixAtoms
from mattersim.forcefield import MatterSimCalculator

# ========================================
# 🔧 声子谱CSV导出性能优化配置
# ========================================
# 在此处修改配置，无需深入函数内部

# 原子数阈值：超过此值将跳过CSV导出（节省时间）
# 建议值：
#   - 8: 非常严格，只有小分子导出CSV（最快）
#   - 10: 严格模式，大多数复杂结构跳过CSV（推荐）
#   - 15: 平衡模式，中等结构也导出CSV
#   - 20: 宽松模式，只有非常大的结构跳过CSV
#   - 50: 几乎不跳过（最慢）
PHONON_CSV_ATOM_THRESHOLD = 20

# CSV最大行数：超过此值将进行降采样
# 建议值：
#   - 500: 超快速（~50KB，适合快速预览）
#   - 1000: 快速（~100KB，适合可视化）[默认]
#   - 2000: 平衡（~200KB，较详细）
#   - 5000: 高细节（~500KB，科研分析）
#   - -1: 无限制（可能非常慢，不推荐）
PHONON_CSV_MAX_ROWS = 100

# 是否对大结构跳过CSV导出
# True: 启用跳过（推荐，节省时间）
# False: 强制导出所有CSV（可能很慢）
PHONON_CSV_SKIP_LARGE_STRUCTURES = True

# ========================================

# Import MatterSim applications for relaxation and phonon calculations
try:
    from mattersim.applications.relax import Relaxer
    RELAXER_AVAILABLE = True
except ImportError:
    RELAXER_AVAILABLE = False

try:
    from mattersim.applications.phonon import PhononWorkflow
    PHONON_AVAILABLE = True
except ImportError:
    PHONON_AVAILABLE = False

# Optional imports for enhanced functionality
try:
    from scipy.spatial.distance import pdist
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = structlog.get_logger(__name__)

# Lazy imports for GNoME dataset processing
pd = None
Composition = None
ComputedEntry = None
PhaseDiagram = None

# Cache for GNoME data to avoid repeated loading
_gnome_data_cache = None
_model_cache = {}


def _get_yaml_loader():
    """获取最快的 YAML 加载器"""
    try:
        from yaml import CLoader as Loader
        logger.info(f"   ⚡ Using fast C-based YAML loader")
        return Loader
    except ImportError:
        from yaml import SafeLoader as Loader
        logger.info(f"   ⚠️ Using slower Python YAML loader")
        return Loader


def _downsample_dataframe(df, max_rows: int, original_count: int):
    """对 DataFrame 进行降采样"""
    if max_rows <= 0 or max_rows == -1 or original_count <= max_rows:
        if max_rows == -1:
            logger.info(f"   📊 No downsampling (max_csv_rows=-1), exporting all {original_count} rows")
        return df, original_count

    logger.info(f"   ✂️ Downsampling from {original_count} to {max_rows} rows...")
    sample_indices = [0]  # 保留第一个点
    step = original_count / (max_rows - 2)
    sample_indices.extend([int(i * step) for i in range(1, max_rows - 1)])
    sample_indices.append(original_count - 1)  # 保留最后一个点

    df_sampled = df.iloc[sample_indices].reset_index(drop=True)
    logger.warning(f"   ⚠️ Downsampled: {original_count} → {len(df_sampled)} rows")
    return df_sampled, original_count


def _save_csv_optimized(df, csv_path, start_time=None):
    """优化的 CSV 保存"""
    import time
    csv_write_start = time.time()
    df.to_csv(csv_path, index=False, float_format='%.6f', chunksize=1000, mode='w')
    csv_write_time = time.time() - csv_write_start

    if start_time:
        total_time = time.time() - start_time
        return csv_write_time, total_time
    return csv_write_time, csv_write_time


def normalize_cif_content(cif_content: str) -> str:
    """
    Normalize CIF content to ensure it has proper format.
    Adds data_ block if missing.

    Args:
        cif_content: Raw CIF content

    Returns:
        Normalized CIF content with data_ block
    """
    # Strip leading/trailing whitespace
    cif_content = cif_content.strip()

    # Check if it already starts with data_
    if re.match(r'^data_', cif_content, re.IGNORECASE):
        return cif_content

    # If no data_ block found, add one at the beginning
    logger.info("Adding missing data_ block to CIF content")
    return "data_crystal\n" + cif_content


def calculate_energy_from_cif_impl(
    cif_content: str,
    cif_filename: str = "material.cif",
    device: str = "cpu"
) -> Dict[str, Any]:
    """
    Calculate energy properties from CIF file using MatterSim.

    Args:
        cif_content: CIF file content (base64 or plain text)
        cif_filename: Original filename
        device: Computing device ('cuda' or 'cpu')

    Returns:
        Dict with energy properties and calculation results
    """
    logger.info("Starting MatterSim energy calculation", filename=cif_filename)

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="mattersim_")
    temp_dir_path = Path(temp_dir)

    try:
        # Step 1: Decode and save CIF file
        cif_path = temp_dir_path / cif_filename

        try:
            # Try to decode base64
            cif_bytes = base64.b64decode(cif_content)
            cif_text = cif_bytes.decode('utf-8')
            logger.info("CIF content decoded from base64")
        except Exception:
            # Already plain text
            cif_text = cif_content
            logger.info("CIF content is plain text")

        # Normalize CIF content (add data_ block if missing)
        cif_text = normalize_cif_content(cif_text)

        # Save to file
        with open(cif_path, 'w') as f:
            f.write(cif_text)
        logger.info("Saved CIF to temporary file", path=str(cif_path))

        # Step 2: Load structure with ASE and validate
        # 🔧 强制使用 CIF 格式，避免 ASE 根据文件名误判
        structure = ase_io.read(str(cif_path), format='cif')
        composition_str = structure.get_chemical_formula()
        n_atoms = len(structure)
        
        # Validate structure before calculation
        # Validate structure with detailed error reporting
        validation_result = validate_structure(structure)
        if not validation_result:
            # Provide detailed diagnostic information
            try:
                n_atoms = len(structure)
                cell = structure.get_cell()
                cell_lengths = np.linalg.norm(cell, axis=1)
                positions = structure.get_positions()

                error_details = []
                if n_atoms == 0:
                    error_details.append("Structure contains no atoms")
                if not np.all(np.isfinite(cell_lengths)):
                    error_details.append(f"Cell parameters contain NaN/Inf: {cell_lengths}")
                if np.any(cell_lengths < 0.001):
                    error_details.append(f"Cell parameters too small or negative: {cell_lengths} Å")
                if not np.all(np.isfinite(positions)):
                    error_details.append("Atomic positions contain NaN/Inf")

                error_msg = "Invalid structure detected. " + "; ".join(error_details) if error_details else "Unknown validation error"
            except Exception:
                error_msg = "Invalid structure detected. Structure validation failed."

            return {
                "success": False,
                "error": error_msg
            }
        
        logger.info("Loaded and validated structure", composition=composition_str, n_atoms=n_atoms)

        # Step 3: Find MatterSim model
        model_path = _find_mattersim_model()
        if model_path is None:
            return {
                "success": False,
                "error": "MatterSim model not found. Please ensure model files are in mcp_servers/simulation/models/"
            }

        logger.info("Using MatterSim model", model_path=str(model_path))

        # Step 4: Create MatterSim calculator with caching and optimized settings
        try:
            calc = get_calculator_with_cache(model_path, device)
            structure.calc = calc
            logger.info("MatterSim calculator ready", device=device, model=model_path.name)
        except Exception as e:
            logger.error("Failed to create MatterSim calculator", error=str(e))
            return {
                "success": False,
                "error": f"Failed to initialize MatterSim calculator: {str(e)}"
            }

        # Step 5: Calculate properties using MatterSim with enhanced error handling
        try:
            # Calculate total energy with validation
            total_energy = structure.get_potential_energy()  # eV
            if not np.isfinite(total_energy):
                raise ValueError(f"Invalid total energy: {total_energy}")
            
            energy_per_atom = total_energy / n_atoms  # eV/atom
            
            # Calculate forces with validation
            forces = structure.get_forces()  # eV/Å, shape (n_atoms, 3)
            if not np.all(np.isfinite(forces)):
                logger.warning("Some forces are not finite, setting to zero")
                forces = np.nan_to_num(forces, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Calculate force statistics with improved precision
            force_magnitudes = np.linalg.norm(forces, axis=1)  # eV/Å
            forces_max = float(np.max(force_magnitudes))  # eV/Å
            forces_mean = float(np.mean(force_magnitudes))  # eV/Å
            forces_rms = float(np.sqrt(np.mean(force_magnitudes**2)))  # eV/Å (RMS)
            
        except Exception as e:
            logger.error("Failed to calculate energy and forces", error=str(e))
            return {
                "success": False,
                "error": f"Energy/force calculation failed: {str(e)}"
            }
        
        # Calculate stress tensor with enhanced error handling
        # Following MatterSim official documentation:
        # https://microsoft.github.io/mattersim/user_guide/getting_started.html
        try:
            # Get stress tensor in eV/Å³ (3x3 matrix)
            # Following official example: si.get_stress(voigt=False)[0][0]
            stress_tensor_ev_ang3 = structure.get_stress(voigt=False)  # eV/Å³, shape (3,3)

            # Validate stress tensor
            if not np.all(np.isfinite(stress_tensor_ev_ang3)):
                logger.warning("Stress tensor contains non-finite values")
                stress_tensor_ev_ang3 = np.nan_to_num(stress_tensor_ev_ang3, nan=0.0, posinf=0.0, neginf=0.0)

            # Convert to GPa (following official example: stress / GPa)
            # 1 eV/Å³ = 160.2177 GPa
            stress_tensor_gpa = stress_tensor_ev_ang3 / GPa  # GPa, shape (3,3)

            # Extract [0][0] element as shown in official documentation
            stress_00_gpa = float(stress_tensor_gpa[0][0])  # GPa

            # Calculate pressure (negative trace of stress tensor divided by 3)
            stress_trace_ev_ang3 = float(np.trace(stress_tensor_ev_ang3))  # eV/Å³
            pressure_ev_ang3 = -stress_trace_ev_ang3 / 3.0  # eV/Å³
            pressure_gpa = pressure_ev_ang3 / GPa  # GPa

            # Store stress tensor as list for JSON serialization
            stress_tensor_ev_ang3_list = stress_tensor_ev_ang3.tolist()
            stress_tensor_gpa_list = stress_tensor_gpa.tolist()

        except Exception as e:
            logger.warning("Failed to calculate stress tensor", error=str(e))
            stress_trace_ev_ang3 = 0.0
            pressure_ev_ang3 = 0.0
            pressure_gpa = 0.0
            stress_00_gpa = 0.0
            stress_tensor_ev_ang3_list = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
            stress_tensor_gpa_list = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]

        # Calculate additional energy metrics for better analysis
        try:
            # Calculate cohesive energy (approximate)
            cohesive_energy_per_atom = -energy_per_atom  # Rough approximation

            # Calculate energy density
            volume = structure.get_volume()  # Å³
            energy_density = total_energy / volume if volume > 0 else 0.0  # eV/Å³

            logger.info("MatterSim prediction completed",
                       total_energy=total_energy,
                       energy_per_atom=energy_per_atom,
                       forces_max=forces_max,
                       forces_mean=forces_mean,
                       forces_rms=forces_rms,
                       pressure_gpa=pressure_gpa,
                       stress_00_gpa=stress_00_gpa,
                       volume=volume,
                       energy_density=energy_density)
        except Exception as e:
            logger.warning("Failed to calculate additional metrics", error=str(e))
            cohesive_energy_per_atom = 0.0
            energy_density = 0.0
            volume = 0.0

        # Step 6: Calculate formation and decomposition energy using GNoME with caching
        try:
            energy_props = _calculate_energy_properties(
                composition_str=composition_str,
                total_energy=total_energy,
                n_atoms=n_atoms
            )
        except Exception as e:
            logger.warning("Failed to calculate energy properties from GNoME", error=str(e))
            energy_props = {
                "formation_energy_per_atom": 0.0,
                "decomposition_energy": 0.0
            }

        # Step 7: Determine stability with improved thresholds
        decomposition_energy = energy_props.get('decomposition_energy', 0.0)
        formation_energy_per_atom = energy_props.get('formation_energy_per_atom', 0.0)
        
        # Enhanced stability classification
        if decomposition_energy < -0.001:  # More negative threshold for stable
            stability_status = "STABLE"
        elif decomposition_energy < 0.001:  # Very small positive values
            stability_status = "NEARLY_STABLE"
        elif decomposition_energy < 0.1:   # Moderately unstable
            stability_status = "METASTABLE"
        else:
            stability_status = "UNSTABLE"
        
        # Additional stability indicators
        is_force_converged = forces_max < 0.05  # eV/Å threshold for convergence
        is_stress_reasonable = abs(pressure_gpa) < 10.0  # GPa threshold

        logger.info("Energy calculation completed",
                   decomposition_energy=decomposition_energy,
                   status=stability_status,
                   total_energy=total_energy)

        # Generate calculation ID
        calculation_id = str(uuid.uuid4())[:12]

        return {
            "success": True,
            # Basic energy properties
            "total_energy": float(total_energy),  # eV
            "energy_per_atom": float(energy_per_atom),  # eV/atom
            "formation_energy_per_atom": float(formation_energy_per_atom),  # eV/atom
            "decomposition_energy": float(decomposition_energy),  # eV/atom
            "cohesive_energy_per_atom": float(cohesive_energy_per_atom),  # eV/atom
            "energy_density": float(energy_density),  # eV/Å³

            # Force properties
            "forces_max": float(forces_max),  # eV/Å (maximum force on any atom)
            "forces_mean": float(forces_mean),  # eV/Å (mean force magnitude)
            "forces_rms": float(forces_rms),  # eV/Å (RMS force)

            # Stress tensor (following MatterSim official documentation)
            # https://microsoft.github.io/mattersim/user_guide/getting_started.html
            "stress_tensor_ev_ang3": stress_tensor_ev_ang3_list,  # 3x3 matrix in eV/Å³
            "stress_tensor_gpa": stress_tensor_gpa_list,  # 3x3 matrix in GPa
            "stress_00_gpa": float(stress_00_gpa),  # GPa (stress[0][0] element as shown in official docs)

            # Pressure properties (scalar values)
            "pressure_ev_ang3": float(pressure_ev_ang3),  # eV/Å³ (hydrostatic pressure)
            "pressure_gpa": float(pressure_gpa),  # GPa (hydrostatic pressure)

            # Structure properties
            "composition": composition_str,
            "n_atoms": int(n_atoms),
            "volume": float(volume),  # Å³

            # Stability analysis
            "stability_status": stability_status,
            "is_force_converged": bool(is_force_converged),
            "is_stress_reasonable": bool(is_stress_reasonable),

            # Calculation metadata
            "calculation_id": calculation_id,
            "model_used": model_path.name,
            "device": device,
            "calculation_time": None  # Will be added if timing is implemented
        }

    except Exception as e:
        logger.error("Energy calculation failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Energy calculation failed: {str(e)}"
        }

    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            logger.info("Cleaned up temporary directory")
        except Exception as e:
            logger.warning("Failed to cleanup temporary directory", error=str(e))


def _find_mattersim_model() -> Path:
    """
    Find MatterSim model file.

    Returns:
        Path to model file, or None if not found
    """
    # Get the directory of this file
    current_file = Path(__file__).resolve()
    # Go up to mcp_servers/simulation/modules -> mcp_servers/simulation
    simulation_dir = current_file.parent.parent
    models_dir = simulation_dir / "models"

    # Also try from current working directory
    cwd = Path.cwd()

    # Possible model paths (prefer 1M over 5M for better performance on limited resources)
    possible_paths = [
        # Relative to this file's location
        models_dir / "mattersim-v1.0.0-1M" / "mattersim-v1.0.0-1M.pth",
        models_dir / "mattersim-v1.0.0-5M" / "mattersim-v1.0.0-5M.pth",
        # Relative to current working directory
        cwd / "mcp_servers" / "simulation" / "models" / "mattersim-v1.0.0-1M" / "mattersim-v1.0.0-1M.pth",
        cwd / "mcp_servers" / "simulation" / "models" / "mattersim-v1.0.0-5M" / "mattersim-v1.0.0-5M.pth",
        # Simple relative paths
        Path("mcp_servers/simulation/models/mattersim-v1.0.0-1M/mattersim-v1.0.0-1M.pth"),
        Path("mcp_servers/simulation/models/mattersim-v1.0.0-5M/mattersim-v1.0.0-5M.pth"),
        Path("models/mattersim-v1.0.0-1M/mattersim-v1.0.0-1M.pth"),
        Path("models/mattersim-v1.0.0-5M/mattersim-v1.0.0-5M.pth"),
    ]

    logger.info("Searching for MatterSim model",
               current_file=str(current_file),
               simulation_dir=str(simulation_dir),
               models_dir=str(models_dir),
               cwd=str(cwd))

    for path in possible_paths:
        logger.debug("Checking path", path=str(path), exists=path.exists())
        if path.exists():
            logger.info("Found MatterSim model", path=str(path))
            return path

    logger.error("MatterSim model not found", searched_paths=[str(p) for p in possible_paths])
    return None


def _calculate_energy_properties(
    composition_str: str,
    total_energy: float,
    n_atoms: int
) -> Dict[str, Any]:
    """
    Calculate formation energy and decomposition energy using GNoME dataset.
    
    Enhanced with better error handling, validation, and caching.

    Args:
        composition_str: Chemical composition string
        total_energy: Total energy in eV
        n_atoms: Number of atoms

    Returns:
        Dict with formation_energy_per_atom and decomposition_energy
    """
    # Lazy import heavy dependencies
    global pd, Composition, ComputedEntry, PhaseDiagram

    if pd is None:
        try:
            import pandas as pd_module
            from pymatgen.core import Composition as Comp
            from pymatgen.entries.computed_entries import ComputedEntry as CE
            from pymatgen.analysis.phase_diagram import PhaseDiagram as PD

            pd = pd_module
            Composition = Comp
            ComputedEntry = CE
            PhaseDiagram = PD

            logger.info("Loaded pymatgen and pandas for energy calculations")
        except ImportError as e:
            logger.warning(f"Cannot load pymatgen/pandas: {e}, skipping energy properties")
            return {
                "formation_energy_per_atom": 0.0,
                "decomposition_energy": 0.0
            }

    # Validate inputs
    if not composition_str or not isinstance(composition_str, str):
        logger.warning("Invalid composition string", composition=composition_str)
        return {"formation_energy_per_atom": 0.0, "decomposition_energy": 0.0}
    
    if not np.isfinite(total_energy):
        logger.warning("Invalid total energy", energy=total_energy)
        return {"formation_energy_per_atom": 0.0, "decomposition_energy": 0.0}

    try:
        # Load GNoME data with caching
        minimal_entries, grouped_entries = _load_gnome_data()
        
        if minimal_entries is None or len(minimal_entries) == 0:
            logger.warning("No GNoME data available")
            return {"formation_energy_per_atom": 0.0, "decomposition_energy": 0.0}

        # Create entry with validation
        try:
            composition = Composition(composition_str)
        except Exception as e:
            logger.warning(f"Failed to parse composition: {e}", composition=composition_str)
            return {"formation_energy_per_atom": 0.0, "decomposition_energy": 0.0}
        
        sample_entry = ComputedEntry(composition=composition, energy=total_energy)

        # Get chemical system
        chemsys = [str(el) for el in composition.elements]
        logger.debug("Processing chemical system", chemsys=chemsys)

        # Gather convex hull entries
        mg_entries = _gather_convex_hull(chemsys, grouped_entries, minimal_entries)
        
        if not mg_entries:
            logger.warning("No convex hull entries found", chemsys=chemsys)
            return {"formation_energy_per_atom": 0.0, "decomposition_energy": 0.0}

        # Compute phase diagram with error handling
        try:
            diagram = PhaseDiagram(mg_entries)
        except Exception as e:
            logger.warning(f"Failed to create phase diagram: {e}")
            return {"formation_energy_per_atom": 0.0, "decomposition_energy": 0.0}

        # Calculate decomposition energy (energy above hull)
        try:
            decomposition, decomposition_energy = diagram.get_decomp_and_e_above_hull(
                sample_entry,
                allow_negative=True
            )
            
            # Validate decomposition energy
            if not np.isfinite(decomposition_energy):
                logger.warning("Invalid decomposition energy calculated")
                decomposition_energy = 0.0
                
        except Exception as e:
            logger.warning(f"Failed to calculate decomposition energy: {e}")
            decomposition_energy = 0.0

        # Calculate formation energy
        try:
            formation_energy = diagram.get_form_energy_per_atom(sample_entry)
            
            # Validate formation energy
            if not np.isfinite(formation_energy):
                logger.warning("Invalid formation energy calculated")
                formation_energy = 0.0
                
        except Exception as e:
            logger.warning(f"Failed to calculate formation energy: {e}")
            formation_energy = 0.0

        logger.debug("Energy properties calculated",
                    formation_energy=formation_energy,
                    decomposition_energy=decomposition_energy)

        return {
            "formation_energy_per_atom": float(formation_energy),
            "decomposition_energy": float(decomposition_energy)
        }

    except Exception as e:
        logger.warning(f"Failed to calculate energy properties: {e}", exc_info=True)
        return {
            "formation_energy_per_atom": 0.0,
            "decomposition_energy": 0.0
        }


def _load_gnome_data():
    """Load GNoME dataset for phase diagram calculations with caching."""
    global _gnome_data_cache
    
    # Return cached data if available
    if _gnome_data_cache is not None:
        logger.debug("Using cached GNoME data")
        return _gnome_data_cache
    
    import json
    import itertools

    # Get the directory of this file
    current_file = Path(__file__).resolve()
    simulation_dir = current_file.parent.parent
    data_dir = simulation_dir / "data"

    # Load stable materials
    stable_path = data_dir / "stable_materials_summary.csv"
    external_path = data_dir / "external_materials_summary.csv"

    # Fallback paths
    if not stable_path.exists():
        stable_path = Path("mcp_servers/simulation/data/stable_materials_summary.csv")
    if not external_path.exists():
        external_path = Path("mcp_servers/simulation/data/external_materials_summary.csv")

    if not stable_path.exists():
        stable_path = Path("data/stable_materials_summary.csv")
    if not external_path.exists():
        external_path = Path("data/external_materials_summary.csv")

    # Check if files exist
    if not stable_path.exists() or not external_path.exists():
        logger.warning("GNoME data files not found", 
                      stable_exists=stable_path.exists(),
                      external_exists=external_path.exists())
        return None, None

    logger.info("Loading GNoME data", stable_path=str(stable_path), external_path=str(external_path))

    try:
        # Load datasets with index_col=0 for stable materials (like reference code)
        gnome_crystals = pd.read_csv(stable_path, index_col=0)
        reference_crystals = pd.read_csv(external_path)

        # Annotate chemical system
        gnome_crystals = _annotate_chemical_system(gnome_crystals)
        reference_crystals = _annotate_chemical_system(reference_crystals)

        # Combine datasets
        all_crystals = pd.concat([gnome_crystals, reference_crystals], ignore_index=True)

        # Create minimal entries with required columns
        required_columns = ['Composition', 'NSites', 'Corrected Energy', 'Formation Energy Per Atom', 'Chemical System']
        
        # Check if all required columns exist
        missing_columns = [col for col in required_columns if col not in all_crystals.columns]
        if missing_columns:
            logger.warning("Missing required columns in GNoME data", missing=missing_columns)
            return None, None
        
        minimal_entries = all_crystals[required_columns]

        # Group by chemical system
        grouped_entries = minimal_entries.groupby('Chemical System')

        logger.info("Loaded GNoME data", n_entries=len(minimal_entries), n_systems=len(grouped_entries))

        # Cache the data
        _gnome_data_cache = (minimal_entries, grouped_entries)
        
        return minimal_entries, grouped_entries
        
    except Exception as e:
        logger.error("Failed to load GNoME data", error=str(e))
        return None, None


def _annotate_chemical_system(crystals):
    """Annotate DataFrame with chemical system."""
    import json

    chemical_systems = []
    for e in crystals['Elements']:
        chemsys = json.loads(e.replace("'", '"'))
        chemical_systems.append(tuple(sorted(chemsys)))
    crystals['Chemical System'] = chemical_systems
    return crystals


def _gather_convex_hull(chemsys, grouped_entries, minimal_entries):
    """Gather convex hull entries for phase diagram."""
    import itertools

    phase_diagram_entries = []

    # Get all subsets of the chemical system
    for length in range(len(chemsys) + 1):
        for subsystem in itertools.combinations(chemsys, length):
            subsystem_key = tuple(sorted(subsystem))
            subsystem_entries = grouped_entries.groups.get(subsystem_key, [])

            if len(subsystem_entries):
                phase_diagram_entries.append(minimal_entries.iloc[subsystem_entries])

    if phase_diagram_entries:
        phase_diagram_entries = pd.concat(phase_diagram_entries)
    else:
        # Return empty list if no entries found
        logger.warning("No phase diagram entries found for chemical system", chemsys=chemsys)
        return []

    # Convert to ComputedEntries
    mg_entries = []

    for _, row in phase_diagram_entries.iterrows():
        composition = row['Composition']
        formation_energy = row['Corrected Energy']  # Use 'Corrected Energy' column
        entry = ComputedEntry(composition, formation_energy)
        mg_entries.append(entry)

    # Add entries with 0 formation energy for every element
    for element in chemsys:
        elemental_entry = ComputedEntry(element, 0.0)
        mg_entries.append(elemental_entry)

    logger.debug("Gathered convex hull entries", n_entries=len(mg_entries), chemsys=chemsys)

    return mg_entries


def clear_cache():
    """Clear all cached data to free memory."""
    global _gnome_data_cache, _model_cache
    _gnome_data_cache = None
    _model_cache.clear()
    logger.info("Cleared all caches")


def get_calculator_with_cache(model_path: Path, device: str = "cpu") -> MatterSimCalculator:
    """
    Get MatterSim calculator with caching to avoid repeated model loading.
    
    Args:
        model_path: Path to the model file
        device: Computing device ('cuda' or 'cpu')
        
    Returns:
        MatterSimCalculator instance
    """
    cache_key = (str(model_path), device)
    
    if cache_key in _model_cache:
        logger.debug("Using cached MatterSim calculator", model=model_path.name, device=device)
        return _model_cache[cache_key]
    
    try:
        # Force CPU device if CUDA is not available
        actual_device = device
        if device == "cuda" and not torch.cuda.is_available():
            actual_device = "cpu"
            logger.warning("CUDA requested but not available, falling back to CPU")

        calc = MatterSimCalculator(
            load_path=str(model_path),
            device=actual_device,
            dtype="float64" if actual_device == "cpu" else "float32"
        )

        # Cache the calculator (be careful with memory usage)
        if len(_model_cache) < 3:  # Limit cache size
            _model_cache[cache_key] = calc

        logger.info("Created and cached MatterSim calculator", model=model_path.name, device=actual_device)
        return calc

    except Exception as e:
        logger.error("Failed to create MatterSim calculator", error=str(e))
        # If CUDA fails, try CPU as fallback
        if device == "cuda":
            logger.info("Retrying with CPU device")
            try:
                calc = MatterSimCalculator(
                    load_path=str(model_path),
                    device="cpu",
                    dtype="float64"
                )
                logger.info("Successfully created MatterSim calculator on CPU fallback")
                return calc
            except Exception as e2:
                logger.error("CPU fallback also failed", error=str(e2))
                raise e2
        raise


def validate_structure(structure) -> bool:
    """验证 ASE 结构的基本有效性"""
    try:
        if len(structure) == 0:
            logger.error("❌ Structure has no atoms")
            return False

        cell_lengths = np.linalg.norm(structure.get_cell(), axis=1)
        if not np.all(np.isfinite(cell_lengths)) or np.any(cell_lengths < 0.001):
            logger.error(f"❌ Invalid cell parameters: {cell_lengths}")
            return False

        if not np.all(np.isfinite(structure.get_positions())):
            logger.error("❌ Invalid atomic positions")
            return False

        formula = structure.get_chemical_formula()
        logger.info(f"✅ Validated: {formula}, {len(structure)} atoms, "
                   f"cell: {cell_lengths[0]:.2f}×{cell_lengths[1]:.2f}×{cell_lengths[2]:.2f} Å")
        return True

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        return False


def _clean_cif_content(cif_content: str) -> str:
    """简化的 CIF 内容清理"""
    cif_content = cif_content.replace('\r\n', '\n').replace('\r', '\n')
    cif_content = re.sub(r'\n\n+', '\n', cif_content)
    lines = [line.encode('ascii', 'ignore').decode('ascii').rstrip()
             for line in cif_content.split('\n') if line.strip()]
    return normalize_cif_content('\n'.join(lines))


def relax_structure_impl(
    cif_content: str,
    cif_filename: str = "material.cif",
    device: str = "cpu",
    optimizer: str = "BFGS",
    filter_type: str = "ExpCellFilter",
    constrain_symmetry: bool = True,
    max_steps: int = 500,
    fmax: float = 0.01
) -> Dict[str, Any]:
    """
    Perform structure relaxation using MatterSim.

    Based on: https://microsoft.github.io/mattersim/examples/relax_example.html

    Args:
        cif_content: CIF file content (base64 or plain text)
        cif_filename: Original filename
        device: Computing device ('cuda' or 'cpu')
        optimizer: Optimization method ('BFGS', 'FIRE', 'LBFGS')
        filter_type: Filter to apply to the cell ('ExpCellFilter', 'FrechetCellFilter', None)
        constrain_symmetry: Whether to constrain the symmetry during relaxation
        max_steps: Maximum number of optimization steps
        fmax: Force convergence criterion (eV/Å)

    Returns:
        Dict with relaxed structure and relaxation results
    """
    if not RELAXER_AVAILABLE:
        return {
            "success": False,
            "error": "MatterSim Relaxer not available. Please install mattersim with: pip install mattersim"
        }

    logger.info("Starting MatterSim structure relaxation", filename=cif_filename)

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="mattersim_relax_")
    temp_dir_path = Path(temp_dir)

    try:
        # Step 1: Decode and save CIF file
        cif_path = temp_dir_path / cif_filename

        try:
            cif_bytes = base64.b64decode(cif_content)
            cif_text = cif_bytes.decode('utf-8')
            logger.info("CIF content decoded from base64")
        except Exception:
            cif_text = cif_content
            logger.info("CIF content is plain text")

        # Normalize CIF content (add data_ block if missing)
        cif_text = normalize_cif_content(cif_text)

        with open(cif_path, 'w') as f:
            f.write(cif_text)
        logger.info("Saved CIF to temporary file", path=str(cif_path))

        # Step 2: Load structure with ASE and validate
        # 🔧 关键修复：强制使用 CIF 格式，避免 ASE 根据文件名误判（如 POSCAR.cif 被当作 VASP 文件）
        try:
            structure = ase_io.read(str(cif_path), format='cif')
            composition_str = structure.get_chemical_formula()
            n_atoms = len(structure)
            logger.info(f"✅ Successfully parsed CIF with ASE: {composition_str}, {n_atoms} atoms")
        except StopIteration as e:
            # This specific error usually means the CIF file is empty or has no structure data
            logger.error("CIF file appears to be empty or missing structure data", error=str(e))
            return {
                "success": False,
                "error": "CIF file is empty or missing structure data. Please ensure the file contains complete crystal structure information including lattice parameters and atomic positions."
            }
        except Exception as e:
            logger.warning(f"⚠️ Initial CIF parsing failed: {str(e)}, attempting to clean and retry...")
            # Try to clean up the CIF content and retry
            try:
                logger.info("Attempting to normalize and clean CIF content...")
                cleaned_cif = _clean_cif_content(cif_text)
                with open(cif_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_cif)
                structure = ase_io.read(str(cif_path), format='cif')
                composition_str = structure.get_chemical_formula()
                n_atoms = len(structure)
                logger.info(f"✅ Successfully parsed CIF after cleaning: {composition_str}, {n_atoms} atoms")
            except StopIteration as e2:
                logger.error("CIF file appears to be empty even after cleaning", error=str(e2))
                return {
                    "success": False,
                    "error": "CIF file is empty or missing structure data. Please ensure the file contains complete crystal structure information."
                }
            except Exception as e2:
                logger.error(f"❌ Failed to parse CIF even after cleaning: {str(e2)}")

                # 🔧 最后的尝试：使用 pymatgen 重新生成 CIF
                try:
                    logger.info("🔧 Attempting to regenerate CIF using pymatgen...")
                    from pymatgen.core import Structure as PymatgenStructure
                    from pymatgen.io.cif import CifParser
                    from io import StringIO

                    # 尝试用 pymatgen 解析
                    parser = CifParser(StringIO(cif_text))
                    pmg_structure = parser.get_structures()[0]

                    # 重新生成干净的 CIF
                    from pymatgen.io.cif import CifWriter
                    writer = CifWriter(pmg_structure, symprec=0.01)
                    regenerated_cif = str(writer)

                    # 🔧 清理 pymatgen 生成的 CIF 中可能导致 ASE 解析错误的字段
                    lines = regenerated_cif.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        # 跳过可能导致 ASE 解析错误的对称性字段
                        if line.strip().startswith('_symmetry_Int_Tables_number'):
                            logger.info("🔧 Removing _symmetry_Int_Tables_number from regenerated CIF")
                            continue
                        if line.strip().startswith('_space_group_IT_number'):
                            logger.info("🔧 Removing _space_group_IT_number from regenerated CIF")
                            continue

                        # 🔧 修复空间群名称中的下标问题
                        # pymatgen 使用 _1, _2 等表示下标，但 ASE 不识别
                        if line.strip().startswith('_symmetry_space_group_name_H-M'):
                            line = line.replace('_1', '1').replace('_2', '2').replace('_3', '3').replace('_4', '4').replace('_6', '6')
                            logger.info(f"🔧 Fixed space group name subscripts: {line.strip()}")

                        cleaned_lines.append(line)

                    regenerated_cif = '\n'.join(cleaned_lines)

                    # 保存并重新尝试
                    with open(cif_path, 'w', encoding='utf-8') as f:
                        f.write(regenerated_cif)

                    # 🔧 强制使用 CIF 格式
                    structure = ase_io.read(str(cif_path), format='cif')
                    composition_str = structure.get_chemical_formula()
                    n_atoms = len(structure)
                    logger.info(f"✅ Successfully parsed CIF after pymatgen regeneration: {composition_str}, {n_atoms} atoms")

                except Exception as e3:
                    logger.error(f"❌ Failed to regenerate CIF with pymatgen: {str(e3)}")
                    # Provide helpful error message based on the error type
                    error_msg = f"Failed to parse CIF file. "
                    if "scaling" in str(e).lower() or "scaling" in str(e2).lower():
                        error_msg += "The file contains invalid symmetry or lattice parameter scaling factors. "
                    elif "data_" in str(e2).lower():
                        error_msg += "The file may be missing a 'data_' block declaration. "
                    elif "cell" in str(e2).lower():
                        error_msg += "The file may be missing lattice parameters (_cell_length_a, _cell_length_b, etc.). "
                    elif "atom" in str(e2).lower():
                        error_msg += "The file may be missing atomic position data (_atom_site_*). "

                    error_msg += f"\n\nOriginal error: {str(e)}\nAfter cleaning: {str(e2)}\nAfter pymatgen: {str(e3)}"

                    return {
                        "success": False,
                        "error": error_msg
                    }

        # Validate structure with detailed error reporting
        if not validate_structure(structure):
            # Provide detailed diagnostic information
            try:
                n_atoms = len(structure)
                cell = structure.get_cell()
                cell_lengths = np.linalg.norm(cell, axis=1)
                positions = structure.get_positions()

                error_details = []
                if n_atoms == 0:
                    error_details.append("Structure contains no atoms")
                if not np.all(np.isfinite(cell_lengths)):
                    error_details.append(f"Cell parameters contain NaN/Inf: {cell_lengths}")
                if np.any(cell_lengths < 0.001):
                    error_details.append(f"Cell parameters too small or negative: {cell_lengths} Å")
                if not np.all(np.isfinite(positions)):
                    error_details.append("Atomic positions contain NaN/Inf")

                error_msg = "Invalid structure detected. " + "; ".join(error_details) if error_details else "Unknown validation error"
            except Exception:
                error_msg = "Invalid structure detected. Structure validation failed."

            return {
                "success": False,
                "error": error_msg
            }

        logger.info("Loaded and validated structure", composition=composition_str, n_atoms=n_atoms)

        # Step 3: Find MatterSim model
        model_path = _find_mattersim_model()
        if model_path is None:
            return {
                "success": False,
                "error": "MatterSim model not found. Please ensure model files are in mcp_servers/simulation/models/"
            }

        logger.info("Using MatterSim model", model_path=str(model_path))

        # Step 4: Create MatterSim calculator
        try:
            calc = get_calculator_with_cache(model_path, device)
            structure.calc = calc
            logger.info("MatterSim calculator ready", device=device, model=model_path.name)
        except Exception as e:
            logger.error("Failed to create MatterSim calculator", error=str(e))
            return {
                "success": False,
                "error": f"Failed to initialize MatterSim calculator: {str(e)}"
            }

        # Step 5: Get initial energy
        try:
            initial_energy = structure.get_potential_energy()
            initial_forces = structure.get_forces()
            initial_max_force = float(np.max(np.linalg.norm(initial_forces, axis=1)))
            logger.info("Initial state", energy=initial_energy, max_force=initial_max_force)
        except Exception as e:
            logger.error("Failed to calculate initial energy", error=str(e))
            return {
                "success": False,
                "error": f"Failed to calculate initial energy: {str(e)}"
            }

        # Step 6: Perform relaxation using MatterSim Relaxer
        try:
            relaxer = Relaxer(
                optimizer=optimizer,
                filter=filter_type,
                constrain_symmetry=constrain_symmetry
            )

            logger.info("Starting relaxation", optimizer=optimizer, filter=filter_type,
                       constrain_symmetry=constrain_symmetry, max_steps=max_steps, fmax=fmax)

            result = relaxer.relax(structure, steps=max_steps, fmax=fmax)

            # Handle different return types from relaxer.relax()
            # It may return:
            # 1. An Atoms object directly
            # 2. A tuple (converged: bool, relaxed_structure: Atoms)
            # 3. A tuple (relaxed_structure: Atoms, trajectory)
            if isinstance(result, tuple):
                # Check if first element is bool (converged flag)
                if isinstance(result[0], bool):
                    converged, relaxed_structure = result
                    logger.info("Relaxation completed", converged=converged)
                else:
                    # First element is Atoms object
                    relaxed_structure = result[0]
                    logger.info("Relaxation completed successfully (with trajectory)")
            else:
                relaxed_structure = result
                logger.info("Relaxation completed successfully")

        except Exception as e:
            logger.error("Relaxation failed", error=str(e))
            return {
                "success": False,
                "error": f"Structure relaxation failed: {str(e)}"
            }

        # Step 7: Get final energy and forces
        try:
            final_energy = relaxed_structure.get_potential_energy()
            final_forces = relaxed_structure.get_forces()
            final_max_force = float(np.max(np.linalg.norm(final_forces, axis=1)))
            final_mean_force = float(np.mean(np.linalg.norm(final_forces, axis=1)))

            energy_change = final_energy - initial_energy
            force_change = final_max_force - initial_max_force

            logger.info("Final state", energy=final_energy, max_force=final_max_force,
                       energy_change=energy_change, force_change=force_change)

        except Exception as e:
            logger.error("Failed to calculate final energy", error=str(e))
            return {
                "success": False,
                "error": f"Failed to calculate final energy: {str(e)}"
            }

        # Step 8: Save relaxed structure to CIF
        relaxed_cif_path = temp_dir_path / f"relaxed_{cif_filename}"
        try:
            # Validate relaxed structure before saving
            if relaxed_structure is None or len(relaxed_structure) == 0:
                raise ValueError("Relaxed structure is empty or None")

            ase_io.write(str(relaxed_cif_path), relaxed_structure, format='cif')

            # Verify file exists and has content
            if not relaxed_cif_path.exists() or relaxed_cif_path.stat().st_size == 0:
                raise IOError(f"Failed to write CIF file: {relaxed_cif_path}")

            # Read the relaxed CIF content
            with open(relaxed_cif_path, 'r') as f:
                relaxed_cif_content = f.read()

            if not relaxed_cif_content.strip():
                 raise ValueError("Generated CIF content is empty")

            # Encode to base64
            relaxed_cif_base64 = base64.b64encode(relaxed_cif_content.encode('utf-8')).decode('utf-8')

            logger.info("Saved relaxed structure to CIF", path=str(relaxed_cif_path))

        except Exception as e:
            logger.error("Failed to save relaxed structure", error=str(e))
            return {
                "success": False,
                "error": f"Failed to save relaxed structure to CIF: {str(e)}"
            }

        # Step 9: Calculate structure changes
        try:
            initial_volume = structure.get_volume()
            final_volume = relaxed_structure.get_volume()
            volume_change = final_volume - initial_volume
            volume_change_percent = (volume_change / initial_volume) * 100

            # Calculate lattice parameter changes
            initial_cell = structure.get_cell()
            final_cell = relaxed_structure.get_cell()
            cell_change = np.linalg.norm(final_cell - initial_cell)

            logger.info("Structure changes", volume_change=volume_change,
                       volume_change_percent=volume_change_percent, cell_change=cell_change)

        except Exception as e:
            logger.warning("Failed to calculate structure changes", error=str(e))
            volume_change = 0.0
            volume_change_percent = 0.0
            cell_change = 0.0

        # Generate calculation ID
        calculation_id = str(uuid.uuid4())[:12]

        return {
            "success": True,
            # Relaxation results
            "converged": final_max_force < fmax,
            "steps_performed": max_steps,  # Note: Relaxer doesn't return actual steps

            # Energy results
            "initial_energy": float(initial_energy),
            "final_energy": float(final_energy),
            "energy_change": float(energy_change),
            "energy_per_atom": float(final_energy / n_atoms),

            # Force results
            "initial_max_force": float(initial_max_force),
            "final_max_force": float(final_max_force),
            "final_mean_force": float(final_mean_force),
            "force_change": float(force_change),
            "fmax_criterion": float(fmax),

            # Structure results
            "initial_volume": float(initial_volume),
            "final_volume": float(final_volume),
            "volume_change": float(volume_change),
            "volume_change_percent": float(volume_change_percent),
            "cell_change": float(cell_change),

            # Relaxed structure
            # ⚠️ TOKEN OPTIMIZATION: Return CIF content for server processing, but mark for removal
            # Server will save to file and remove content before returning to client
            "relaxed_cif_content": relaxed_cif_content,  # Needed by server for file saving
            "relaxed_cif_base64": relaxed_cif_base64,    # Kept for backward compatibility
            "relaxed_cif_filename": f"relaxed_{cif_filename}",
            "_remove_cif_content_before_return": True,  # Flag for server to remove large content

            # Structure properties
            "composition": composition_str,
            "n_atoms": int(n_atoms),

            # Calculation metadata
            "calculation_id": calculation_id,
            "model_used": model_path.name,
            "device": device,
            "optimizer": optimizer,
            "filter": filter_type,
            "constrain_symmetry": constrain_symmetry
        }

    except Exception as e:
        logger.error("Structure relaxation failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Structure relaxation failed: {str(e)}"
        }

    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            logger.info("Cleaned up temporary directory")
        except Exception as e:
            logger.warning("Failed to cleanup temporary directory", error=str(e))


def calculate_phonon_impl(
    cif_content: str,
    cif_filename: str = "material.cif",
    device: str = "cpu",
    supercell_matrix: Optional[List[int]] = None,
    amplitude: float = 0.01,
    find_prim: bool = True,
    output_dir: Optional[str] = None,
    max_csv_rows: int = 1000,
    skip_csv_for_large_structures: bool = True,
    large_structure_threshold: int = 10
) -> Dict[str, Any]:
    """
    Calculate phonon dispersion using MatterSim.

    Results are saved to the specified output directory (or default persistent directory).
    This avoids duplicate file saves and ensures images go directly to the target location.

    ⚠️ 注意：计算完成后，YAML文件会被自动清理，只保留图片和CSV文件。

    Based on: https://microsoft.github.io/mattersim/examples/phonon_example.html

    Args:
        cif_content: CIF file content (base64 or plain text)
        cif_filename: Original filename
        device: Computing device ('cuda' or 'cpu')
        supercell_matrix: Supercell matrix for phonon calculation (default: [2, 2, 2])
        amplitude: Displacement amplitude for phonon calculation (default: 0.01 Å)
        find_prim: Whether to find primitive cell before calculation (default: True)
        output_dir: Target directory for saving images (if None, uses default phonon_results/)
        max_csv_rows: Maximum rows in CSV files (default: 1000). If exceeded, data will be downsampled.
                     Set to 0 to disable CSV export entirely.
                     Recommended values:
                     - 500: Ultra-fast export (~50KB CSV, minimal detail)
                     - 1000: Fast export, suitable for visualization (~100KB CSV) [DEFAULT]
                     - 2000: Balanced performance (~200KB CSV)
                     - 5000: High detail (~500KB CSV)
                     - -1: No limit (may be very slow for large datasets)
        skip_csv_for_large_structures: If True, skip CSV export for structures with more atoms than threshold (default: True)
        large_structure_threshold: Number of atoms threshold for skipping CSV export (default: 10)

    Returns:
        Dict with phonon calculation results including image file paths

    Performance Notes:
        - CSV export speed depends on YAML parsing (install libyaml for 5-10x speedup)
        - Large CSV files (>10MB) may take 10-30 seconds to save
        - Images are saved instantly via file move operations
        - Downsampling preserves data quality for visualization while improving performance
    """

    # 使用全局配置（在文件顶部定义，方便修改）
    # 如果函数参数提供了值，则使用参数值；否则使用全局配置
    ATOM_THRESHOLD = large_structure_threshold if large_structure_threshold != 10 else PHONON_CSV_ATOM_THRESHOLD
    MAX_CSV_ROWS = max_csv_rows if max_csv_rows != 1000 else PHONON_CSV_MAX_ROWS
    SKIP_LARGE_CSV = skip_csv_for_large_structures if skip_csv_for_large_structures != True else PHONON_CSV_SKIP_LARGE_STRUCTURES

    if not PHONON_AVAILABLE:
        return {
            "success": False,
            "error": "MatterSim PhononWorkflow not available. Please install mattersim with phonopy support"
        }

    logger.info("Starting MatterSim phonon calculation", filename=cif_filename)

    # 🔧 优化：为每个计算创建独立的子目录，避免文件名冲突
    # Generate unique calculation ID (UUID + timestamp)
    import uuid
    from datetime import datetime

    calculation_id = str(uuid.uuid4())[:8]  # 短 UUID（8 字符）
    calculation_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 精确到毫秒

    # Extract base filename for directory naming
    import re
    base_filename = Path(cif_filename).stem
    base_filename = re.sub(r'^relaxed_', '', base_filename)
    # Sanitize filename (remove special characters)
    safe_filename = re.sub(r'[^\w\-]', '_', base_filename)

    # Create structure-specific subdirectory
    # Format: {base_filename}_{calculation_id}
    structure_dir_name = f"{safe_filename}_{calculation_id}"

    # Determine base output directory
    if output_dir:
        base_output_dir = Path(output_dir)
        logger.info(f"📁 Using provided base output directory: {base_output_dir}")
    else:
        base_output_dir = Path(__file__).parent.parent / "phonon_results"
        logger.info(f"📁 Using default base output directory: {base_output_dir}")

    # Create structure-specific subdirectory
    persistent_dir = base_output_dir / structure_dir_name
    persistent_dir.mkdir(parents=True, exist_ok=True)

    # 使用持久化目录作为工作目录（不再使用临时目录）
    work_dir = str(persistent_dir)
    work_dir_path = persistent_dir

    logger.info(f"✅ Structure-specific directory created: {persistent_dir}")
    logger.info(f"📋 Calculation ID: {calculation_id}")
    logger.info(f"⏰ Calculation timestamp: {calculation_timestamp}")

    # Set default supercell matrix
    if supercell_matrix is None:
        supercell_matrix = [2, 2, 2]

    try:
        # Step 1: Decode and save CIF file to persistent directory
        cif_path = work_dir_path / cif_filename

        try:
            cif_bytes = base64.b64decode(cif_content)
            cif_text = cif_bytes.decode('utf-8')
            logger.info("CIF content decoded from base64")
        except Exception:
            cif_text = cif_content
            logger.info("CIF content is plain text")

        # Normalize CIF content (add data_ block if missing)
        cif_text = normalize_cif_content(cif_text)

        with open(cif_path, 'w') as f:
            f.write(cif_text)
        logger.info("✅ Saved CIF to work directory", path=str(cif_path))

        # Step 2: Load structure with ASE and validate
        # 🔧 强制使用 CIF 格式，避免 ASE 根据文件名误判
        try:
            structure = ase_io.read(str(cif_path), format='cif')
        except StopIteration:
            logger.error("Failed to parse CIF file - file may be empty or invalid")
            return {
                "success": False,
                "error": "Failed to parse CIF file. The file appears to be empty or has invalid format. Please ensure the CIF file contains complete structure data including atomic positions."
            }
        except Exception as e:
            logger.error("Failed to read CIF file", error=str(e))
            return {
                "success": False,
                "error": f"Failed to read CIF file: {str(e)}"
            }

        composition_str = structure.get_chemical_formula()
        n_atoms = len(structure)

        # 🚀 性能优化：大体系跳过CSV导出或只保存total_dos.dat的CSV
        skip_large_csv = SKIP_LARGE_CSV and n_atoms > ATOM_THRESHOLD
        if skip_large_csv:
            logger.info(f"⚡ Large system detected ({n_atoms} atoms > {ATOM_THRESHOLD}), skipping CSV export")
            logger.info(f"   Reason: CSV export for large structures is very slow (can take 30+ seconds)")
            logger.info(f"   Images will still be generated. To force CSV export, set skip_csv_for_large_structures=False")
            logger.info(f"   💡 Tip: Adjust ATOM_THRESHOLD at the top of calculate_phonon_impl() to change this behavior")

        # Extract base name from cif_filename for consistent image naming
        # This ensures image filenames match the original structure name
        # Example: "C.cif" -> "C", "relaxed_C.cif" -> "C"
        import re
        base_filename = Path(cif_filename).stem  # Remove .cif extension
        base_filename = re.sub(r'^relaxed_', '', base_filename)  # Remove "relaxed_" prefix

        # Validate structure with detailed error reporting
        if not validate_structure(structure):
            # Provide detailed diagnostic information
            try:
                n_atoms = len(structure)
                cell = structure.get_cell()
                cell_lengths = np.linalg.norm(cell, axis=1)
                positions = structure.get_positions()

                error_details = []
                if n_atoms == 0:
                    error_details.append("Structure contains no atoms")
                if not np.all(np.isfinite(cell_lengths)):
                    error_details.append(f"Cell parameters contain NaN/Inf: {cell_lengths}")
                if np.any(cell_lengths < 0.001):
                    error_details.append(f"Cell parameters too small or negative: {cell_lengths} Å")
                if not np.all(np.isfinite(positions)):
                    error_details.append("Atomic positions contain NaN/Inf")

                error_msg = "Invalid structure detected. " + "; ".join(error_details) if error_details else "Unknown validation error"
            except Exception:
                error_msg = "Invalid structure detected. Structure validation failed."

            return {
                "success": False,
                "error": error_msg
            }

        logger.info("Loaded and validated structure", composition=composition_str, n_atoms=n_atoms)

        # Step 3: Find MatterSim model
        model_path = _find_mattersim_model()
        if model_path is None:
            return {
                "success": False,
                "error": "MatterSim model not found. Please ensure model files are in mcp_servers/simulation/models/"
            }

        logger.info("Using MatterSim model", model_path=str(model_path))

        # Step 4: Create MatterSim calculator
        try:
            calc = get_calculator_with_cache(model_path, device)
            structure.calc = calc
            logger.info("MatterSim calculator ready", device=device, model=model_path.name)
        except Exception as e:
            logger.error("Failed to create MatterSim calculator", error=str(e))
            return {
                "success": False,
                "error": f"Failed to initialize MatterSim calculator: {str(e)}"
            }

        # Step 5: Set up phonon workflow
        try:
            logger.info("Setting up phonon workflow", supercell=supercell_matrix,
                       amplitude=amplitude, find_prim=find_prim, work_dir=work_dir)

            ph = PhononWorkflow(
                atoms=structure,
                find_prim=find_prim,
                work_dir=work_dir,
                amplitude=amplitude,
                supercell_matrix=np.diag(supercell_matrix)
            )

            logger.info("Phonon workflow created successfully")

        except Exception as e:
            logger.error("Failed to create phonon workflow", error=str(e))
            return {
                "success": False,
                "error": f"Failed to create phonon workflow: {str(e)}"
            }

        # Step 6: Run phonon calculation
        try:
            logger.info("Running phonon calculation (this may take several minutes)...")

            has_imag, phonons = ph.run()

            logger.info("Phonon calculation completed", has_imaginary=has_imag)

        except Exception as e:
            logger.error("Phonon calculation failed", error=str(e))
            return {
                "success": False,
                "error": f"Phonon calculation failed: {str(e)}"
            }

        # Step 7: 定位声子谱图片文件（保留原始文件名）
        try:
            # PhononWorkflow saves plots with format: {chemical_formula}_phonon_band.png
            # e.g., "Si2_phonon_band.png" for Si2
            work_dir_path = Path(work_dir)

            # 🔧 保留原始文件名，不进行重命名
            # Find phonon band plot (search for *_phonon_band.png)
            phonon_band_files = list(work_dir_path.glob("*_phonon_band.png"))

            if phonon_band_files:
                source_plot_path = phonon_band_files[0]
                # 保留原始文件名，不重命名
                plot_exists = True
                plot_relative_path = str(source_plot_path)
                logger.info("✅ Phonon band plot found", path=str(source_plot_path), original_name=source_plot_path.name)
            else:
                # Fallback: try default name
                source_plot_path = work_dir_path / "phonon_band.png"
                if source_plot_path.exists():
                    plot_exists = True
                    plot_relative_path = str(source_plot_path)
                    logger.info("✅ Phonon plot found (default name)", path=str(source_plot_path))
                else:
                    plot_relative_path = ""
                    plot_exists = False
                    logger.warning("⚠️ Phonon plot not found", work_dir=str(work_dir_path))

        except Exception as e:
            logger.warning("Failed to process phonon plot", error=str(e))
            plot_relative_path = ""
            plot_exists = False

        # Step 8: 定位声子态密度图片文件（保留原始文件名）
        dos_relative_path = ""
        dos_exists = False
        try:
            dos_files = list(work_dir_path.glob("*_phonon_dos.png"))
            if dos_files:
                source_dos_path = dos_files[0]
                # 保留原始文件名，不重命名
                dos_exists = True
                dos_relative_path = str(source_dos_path)
                logger.info("✅ Phonon DOS plot found", path=str(source_dos_path), original_name=source_dos_path.name)
        except Exception as e:
            logger.warning("Failed to process phonon DOS plot", error=str(e))

        # ⚠️ TOKEN OPTIMIZATION: Save phonon frequencies to file instead of returning in response
        phonon_data_file = ""
        phonon_dispersion_csv = ""
        phonon_dos_csv = ""

        try:
            import json
            import pandas as pd
            import yaml

            # 🔧 优化：使用标准文件名（在独立目录中）
            phonon_data_file = persistent_dir / "phonon_frequencies.json"

            # Prepare phonon data for saving
            phonon_data = {
                "frequencies": phonons if isinstance(phonons, list) else str(phonons),
                "has_imaginary": bool(has_imag),
                "calculation_id": calculation_id,
                "calculation_timestamp": calculation_timestamp,
                "composition": composition_str,
                "n_atoms": int(n_atoms),
                "supercell_matrix": supercell_matrix,
                "cif_filename": cif_filename,
                "timestamp": datetime.now().isoformat()
            }

            with open(phonon_data_file, 'w', encoding='utf-8') as f:
                json.dump(phonon_data, f, indent=2)

            logger.info(f"💾 Saved phonon frequencies to: {phonon_data_file}")

            # Calculate summary statistics
            if isinstance(phonons, list) and len(phonons) > 0:
                num_frequencies = len(phonons)
                # Try to extract min/max if phonons is a list of numbers
                try:
                    flat_phonons = []
                    if isinstance(phonons[0], (list, tuple)):
                        for item in phonons:
                            flat_phonons.extend(item)
                    else:
                        flat_phonons = phonons
                    min_freq = min(flat_phonons) if flat_phonons else None
                    max_freq = max(flat_phonons) if flat_phonons else None
                except:
                    min_freq = None
                    max_freq = None
            else:
                num_frequencies = 0
                min_freq = None
                max_freq = None

            # 🆕 Extract and save phonon dispersion data from band.yaml (YAML文件稍后会被清理)
            try:
                if MAX_CSV_ROWS == 0:
                    logger.info(f"⏭️ Skipping dispersion CSV export (MAX_CSV_ROWS=0)")
                elif skip_large_csv:
                    logger.info(f"⏭️ Skipping band.yaml CSV export (large system: {n_atoms} atoms > {ATOM_THRESHOLD})")
                else:
                    band_yaml_path = work_dir_path / "band.yaml"
                    if not band_yaml_path.exists():
                        logger.warning(f"⚠️ band.yaml not found")
                    else:
                        import time
                        start_time = time.time()
                        logger.info(f"📊 Extracting phonon dispersion from band.yaml...")

                        with open(band_yaml_path, 'r', encoding='utf-8') as f:
                            band_data = yaml.load(f, Loader=_get_yaml_loader())
                        yaml_load_time = time.time() - start_time
                        logger.info(f"   ⏱️ YAML loaded in {yaml_load_time:.2f}s")

                        if not band_data or 'phonon' not in band_data:
                            logger.warning("⚠️ band.yaml missing 'phonon' key")
                        else:
                            total_points = len(band_data['phonon'])
                            logger.info(f"   📈 Processing {total_points} q-points...")

                            dispersion_rows = []
                            for idx, phonon_point in enumerate(band_data['phonon']):
                                row = {'q_distance': phonon_point.get('distance', 0.0)}
                                for i, band in enumerate(phonon_point.get('band', [])):
                                    row[f'band_{i+1}'] = band.get('frequency', 0.0)
                                dispersion_rows.append(row)
                                if (idx + 1) % 1000 == 0:
                                    logger.info(f"   ⏳ Processed {idx + 1}/{total_points} q-points...")

                            if dispersion_rows:
                                logger.info(f"   🔄 Building DataFrame from {len(dispersion_rows)} rows...")
                                df_dispersion = pd.DataFrame(dispersion_rows)
                                df_dispersion, original_rows = _downsample_dataframe(df_dispersion, MAX_CSV_ROWS, len(df_dispersion))

                                # 🔧 修复：使用与图片文件名一致的命名格式
                                phonon_dispersion_csv = persistent_dir / f"{composition_str}_phonon_dispersion.csv"
                                logger.info(f"   💾 Writing CSV file...")
                                csv_write_time, total_time = _save_csv_optimized(df_dispersion, phonon_dispersion_csv, start_time)

                                logger.info(f"✅ Saved phonon dispersion CSV in {total_time:.2f}s (YAML: {yaml_load_time:.2f}s, CSV: {csv_write_time:.2f}s): {phonon_dispersion_csv}")
                                logger.info(f"   📊 Data shape: {df_dispersion.shape[0]} q-points × {df_dispersion.shape[1]-1} bands")
                                if original_rows > MAX_CSV_ROWS > 0:
                                    logger.info(f"   📉 Original: {original_rows} q-points (downsampled)")
                            else:
                                logger.warning("⚠️ No dispersion data found")
            except Exception as e:
                logger.warning(f"⚠️ Failed to extract phonon dispersion: {e}")

            # 🆕 Extract and save phonon DOS data from mesh.yaml or total_dos.dat
            try:
                if MAX_CSV_ROWS == 0:
                    logger.info(f"⏭️ Skipping DOS CSV export (MAX_CSV_ROWS=0)")
                else:
                    mesh_yaml_path = work_dir_path / "mesh.yaml"
                    dos_dat_path = work_dir_path / "total_dos.dat"
                    dos_extracted = False
                    df_dos = None
                    original_points = 0

                    # 🚀 大体系优化：直接使用 total_dos.dat（跳过慢速的 mesh.yaml）
                    if skip_large_csv:
                        logger.info(f"⚡ Large system: skipping mesh.yaml, using total_dos.dat directly")
                        if dos_dat_path.exists():
                            import time
                            start_time = time.time()
                            logger.info(f"📊 Extracting phonon DOS from total_dos.dat...")
                            df_dos = pd.read_csv(dos_dat_path, sep=r'\s+', header=None,
                                               names=['frequency_THz', 'dos'], comment='#', engine='c')
                            dos_extracted = True
                            logger.info(f"   ✅ Loaded {len(df_dos)} DOS points in {time.time() - start_time:.2f}s")
                        else:
                            logger.warning(f"⚠️ total_dos.dat not found at: {dos_dat_path}")
                    else:
                        # 小体系：优先使用 mesh.yaml
                        if mesh_yaml_path.exists():
                            import time
                            start_time = time.time()
                            logger.info(f"📊 Extracting phonon DOS from mesh.yaml...")

                            with open(mesh_yaml_path, 'r', encoding='utf-8') as f:
                                mesh_data = yaml.load(f, Loader=_get_yaml_loader())
                            yaml_load_time = time.time() - start_time
                            logger.info(f"   ⏱️ YAML loaded in {yaml_load_time:.2f}s")

                            if mesh_data and 'phonon_dos' in mesh_data:
                                logger.info(f"   📈 Processing {len(mesh_data['phonon_dos'])} DOS points...")
                                df_dos = pd.DataFrame(np.array(mesh_data['phonon_dos']),
                                                    columns=['frequency_THz', 'dos'])
                                dos_extracted = True

                        # Fallback to total_dos.dat
                        if not dos_extracted and dos_dat_path.exists():
                            import time
                            start_time = time.time()
                            logger.info(f"📊 Extracting phonon DOS from total_dos.dat...")
                            df_dos = pd.read_csv(dos_dat_path, sep=r'\s+', header=None,
                                               names=['frequency_THz', 'dos'], comment='#', engine='c')
                            dos_extracted = True

                    # Save DOS data
                    if dos_extracted and df_dos is not None:
                        df_dos, original_points = _downsample_dataframe(df_dos, max_csv_rows, len(df_dos))
                        # 🔧 修复：使用与图片文件名一致的命名格式
                        phonon_dos_csv = persistent_dir / f"{composition_str}_phonon_dos.csv"
                        logger.info(f"   💾 Writing CSV file...")
                        csv_write_time, total_time = _save_csv_optimized(df_dos, phonon_dos_csv, start_time if 'start_time' in locals() else None)

                        logger.info(f"✅ Saved phonon DOS CSV in {total_time:.2f}s: {phonon_dos_csv}")
                        logger.info(f"   📊 Data points: {len(df_dos)}")
                        if original_points > max_csv_rows > 0:
                            logger.info(f"   📉 Original: {original_points} points (downsampled)")
                    else:
                        logger.warning(f"⚠️ No DOS data files found")

            except Exception as e:
                logger.warning(f"⚠️ Failed to extract phonon DOS: {e}")

        except Exception as e:
            logger.warning(f"Failed to save phonon frequencies: {e}")
            num_frequencies = 0
            min_freq = None
            max_freq = None

        return {
            "success": True,

            # 🆕 Calculation metadata
            "calculation_id": calculation_id,
            "calculation_timestamp": calculation_timestamp,
            "structure_directory": structure_dir_name,
            "output_directory": str(persistent_dir),

            # Phonon results
            "has_imaginary_modes": bool(has_imag),
            "stability_status": "UNSTABLE" if has_imag else "STABLE",

            # ⚠️ TOKEN OPTIMIZATION: Phonon data saved to file (~90% token reduction)
            "phonon_data_file": str(phonon_data_file) if phonon_data_file else None,
            "phonon_summary": {
                "has_imaginary_modes": bool(has_imag),
                "num_frequencies": num_frequencies,
                "min_frequency": min_freq,
                "max_frequency": max_freq,
                "data_saved_to_file": bool(phonon_data_file)
            },

            # 🆕 Raw data CSV files for frontend display
            "phonon_dispersion_csv": str(phonon_dispersion_csv) if phonon_dispersion_csv else None,
            "phonon_dos_csv": str(phonon_dos_csv) if phonon_dos_csv else None,

            # Plots (file paths for persistent storage - lightweight approach)
            "phonon_band_plot_path": plot_relative_path,
            "phonon_band_plot_available": bool(plot_exists),
            "phonon_dos_plot_path": dos_relative_path,
            "phonon_dos_plot_available": bool(dos_exists),

            # Structure properties
            "composition": composition_str,
            "n_atoms": int(n_atoms),
            "cif_filename": cif_filename,

            # Calculation parameters
            "supercell_matrix": supercell_matrix,
            "amplitude": float(amplitude),
            "find_prim": bool(find_prim),

            # Calculation metadata
            "calculation_id": calculation_id,
            "model_used": model_path.name,
            "device": device,

            # Additional info
            "message": f"Phonon calculation completed. Plot images saved to persistent storage: {plot_relative_path if plot_exists else 'N/A'}, {dos_relative_path if dos_exists else 'N/A'}"
        }

    except Exception as e:
        logger.error("Phonon calculation failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": f"Phonon calculation failed: {str(e)}"
        }

    finally:
        # 🔧 清理YAML文件，只保留图片和CSV文件
        try:
            if 'persistent_dir' in locals():
                yaml_files = list(Path(persistent_dir).glob("*.yaml"))
                for yaml_file in yaml_files:
                    try:
                        yaml_file.unlink()
                        logger.info(f"🗑️ Removed YAML file: {yaml_file.name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to remove YAML file {yaml_file.name}: {e}")

                if yaml_files:
                    logger.info(f"✅ Cleaned up {len(yaml_files)} YAML file(s)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to clean up YAML files: {e}")

        logger.info("✅ Phonon calculation completed, images and CSV files saved to persistent storage")
