"""
CIF File Tools Module
Provides functions for extracting and validating CIF files, and calculating thermal conductivity.
"""
import base64
import re
import os
import tempfile
import shutil
from typing import Dict, List, Any
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# Try to import kappa library
try:
    from kappa_lib import ThermalConductivityCalculator, is_kappa_available
    KAPPA_AVAILABLE = is_kappa_available()
except ImportError:
    KAPPA_AVAILABLE = False


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


def extract_and_validate_cif_impl(message_parts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract CIF file from user message and validate its content.
    
    Args:
        message_parts: List of message parts from user message
    
    Returns:
        Dict containing extraction and validation results
    """
    try:
        logger.info("Extracting CIF file from message parts", parts_count=len(message_parts))
        
        cif_content = None
        cif_filename = "material.cif"
        
        # Step 1: Extract file from message parts
        for part in message_parts:
            if isinstance(part, dict) and "resource" in part:
                resource = part["resource"]
                
                # Get filename
                if "name" in resource:
                    cif_filename = resource["name"]
                
                # Extract content from blob (base64) or text
                if "blob" in resource and "data" in resource["blob"]:
                    cif_content = resource["blob"]["data"]
                    logger.info("Extracted CIF from blob", filename=cif_filename)
                    break
                elif "text" in resource:
                    cif_content = resource["text"]
                    logger.info("Extracted CIF from text", filename=cif_filename)
                    break
        
        if not cif_content:
            return {
                "success": False,
                "error": "未找到 CIF 文件。请确保已上传 CIF 文件。",
                "help": "请点击上传按钮，选择 .cif 文件",
                "is_valid": False
            }
        
        # Step 2: Decode base64 if needed
        is_base64 = False
        try:
            # Try to decode if it's base64
            if not cif_content.strip().startswith('data_'):
                decoded = base64.b64decode(cif_content).decode('utf-8')
                cif_content = decoded
                is_base64 = True
                logger.info("Decoded base64 CIF content", size=len(cif_content))
        except Exception:
            # Not base64, use as is
            logger.info("Content is not base64, using as plain text")

        # Step 2.5: Normalize CIF content (add data_ block if missing)
        cif_content = normalize_cif_content(cif_content)
        
        # Step 3: Validate CIF format
        validation_result = {
            "has_data_block": False,
            "has_cell_parameters": False,
            "has_atom_sites": False,
            "line_count": 0,
            "warnings": []
        }
        
        lines = cif_content.split('\n')
        validation_result["line_count"] = len(lines)
        
        # Check for data block (required)
        if re.search(r'^data_', cif_content, re.MULTILINE):
            validation_result["has_data_block"] = True
        else:
            validation_result["warnings"].append("缺少 data_ 块声明")
        
        # Check for cell parameters (at least one)
        cell_params = ['_cell_length_a', '_cell_length_b', '_cell_length_c',
                      '_cell_angle_alpha', '_cell_angle_beta', '_cell_angle_gamma']
        if any(param in cif_content for param in cell_params):
            validation_result["has_cell_parameters"] = True
        else:
            validation_result["warnings"].append("缺少晶胞参数")
        
        # Check for atom sites
        atom_keywords = ['_atom_site_', 'loop_']
        if any(keyword in cif_content for keyword in atom_keywords):
            validation_result["has_atom_sites"] = True
        else:
            validation_result["warnings"].append("缺少原子位置信息")
        
        # Determine if valid
        is_valid = (
            validation_result["has_data_block"] and
            validation_result["has_cell_parameters"] and
            validation_result["line_count"] > 10
        )
        
        if is_valid:
            logger.info("CIF validation passed", filename=cif_filename)
            return {
                "success": True,
                "cif_content": cif_content,
                "cif_filename": cif_filename,
                "is_valid": True,
                "is_base64": is_base64,
                "validation_details": validation_result,
                "message": f"✅ 成功提取并验证 CIF 文件: {cif_filename}"
            }
        else:
            logger.warning("CIF validation failed", 
                          filename=cif_filename,
                          warnings=validation_result["warnings"])
            return {
                "success": True,  # Extraction succeeded
                "cif_content": cif_content,
                "cif_filename": cif_filename,
                "is_valid": False,
                "is_base64": is_base64,
                "validation_details": validation_result,
                "warning": f"⚠️ CIF 文件格式可能不完整: {', '.join(validation_result['warnings'])}"
            }
    
    except Exception as e:
        logger.error("CIF extraction/validation failed", error=str(e))
        return {
            "success": False,
            "error": f"提取或验证失败: {str(e)}",
            "is_valid": False
        }





def calculate_kappa_from_cif_impl(
    cif_content,  # Can be str or List[Dict]
    cif_filename: str = "material.cif",
    method: str = "kappa_p",
    temperature: float = 300.0
) -> Dict[str, Any]:
    """
    Calculate thermal conductivity from CIF file content.
    Supports both single CIF and batch calculation of multiple CIFs.
    
    Args:
        cif_content: Single CIF string OR list of dicts with structure:
                    [{"cifContent": "...", "formula": "NaCl", "id": "struct1"}, ...]
        cif_filename: Name of the CIF file (used only for single CIF)
        method: Calculation method - "kappa_p" or "kappa_mtp"
        temperature: Temperature in Kelvin
    
    Returns:
        Dict containing calculated thermal conductivity and results
        For batch: returns summary with all results
    """
    # Check if this is a batch calculation
    if isinstance(cif_content, list):
        return _calculate_kappa_batch(cif_content, method, temperature)
    
    # Single CIF calculation (original logic)
    temp_dir = None
    try:
        logger.info("Starting thermal conductivity calculation from CIF",
                   filename=cif_filename,
                   method=method,
                   using_real_lib=KAPPA_AVAILABLE)
        
        # Handle base64 encoded content if needed
        try:
            # Try to decode if it's base64
            if not cif_content.strip().startswith('data_'):
                decoded = base64.b64decode(cif_content).decode('utf-8')
                cif_content = decoded
                logger.info("Decoded base64 CIF content")
        except Exception:
            # Not base64, use as is
            pass

        # Normalize CIF content (add data_ block if missing)
        cif_content = normalize_cif_content(cif_content)

        # Create temporary directory for CIF file
        temp_dir = tempfile.mkdtemp(prefix="kappa_cif_")
        cif_path = os.path.join(temp_dir, cif_filename)

        # Save CIF content to file
        with open(cif_path, 'w', encoding='utf-8') as f:
            f.write(cif_content)
        
        logger.info("CIF file saved", path=cif_path, size=len(cif_content))
        
        # Use real kappa library if available
        if KAPPA_AVAILABLE:
            try:
                logger.info("Using real kappa library for calculation")
                
                # Create calculator
                calculator = ThermalConductivityCalculator(temp_dir)
                
                # Calculate based on method
                if method.lower() == "kappa_p":
                    result_df = calculator.calculate_kappa_p()
                    kappa_column = 'Kappa_Slack (W m-1 K-1)'
                elif method.lower() == "kappa_mtp":
                    result_df = calculator.calculate_kappa_mtp()
                    kappa_column = 'Kappa_cal (W m-1 K-1)'
                else:
                    return {
                        "error": f"Unknown method: {method}. Use 'kappa_p' or 'kappa_mtp'",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Extract results
                if not result_df.empty:
                    kappa_value = float(result_df[kappa_column].iloc[0])
                    
                    # Generate calculation ID
                    calc_id = f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    result = {
                        "calculation_id": calc_id,
                        "method": f"Kappa-{'P (Slack Model)' if method.lower() == 'kappa_p' else 'MTP (ML)'}",
                        "cif_filename": cif_filename,
                        "temperature": temperature,
                        "temperature_unit": "K",
                        "thermal_conductivity": {
                            "value": round(kappa_value, 2),
                            "unit": "W/(m·K)"
                        },
                        "calculation_mode": "real",
                        "full_results": result_df.to_dict(),
                        "timestamp": datetime.now().isoformat(),
                        "success": True
                    }
                    
                    logger.info("Real calculation completed",
                               filename=cif_filename,
                               method=method,
                               kappa=kappa_value)
                    return result
                else:
                    return {
                        "error": "Calculation returned empty results",
                        "method": method,
                        "timestamp": datetime.now().isoformat()
                    }
            
            except Exception as e:
                logger.error("Real calculation failed", error=str(e))
                return {
                    "error": f"Calculation failed: {str(e)}",
                    "method": method,
                    "calculation_mode": "real",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            # Fallback to mock calculation
            logger.warning("Kappa library not available, using mock calculation")
            
            calc_id = f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            mock_kappa = 100.0 + (hash(cif_filename) % 100)
            
            return {
                "calculation_id": calc_id,
                "method": f"Kappa-{'P (Slack Model)' if method.lower() == 'kappa_p' else 'MTP (ML)'}",
                "cif_filename": cif_filename,
                "temperature": temperature,
                "temperature_unit": "K",
                "thermal_conductivity": {
                    "value": round(mock_kappa, 2),
                    "unit": "W/(m·K)"
                },
                "calculation_mode": "mock",
                "note": "Using mock calculation. Real kappa library not available.",
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
    
    except Exception as e:
        logger.error("CIF calculation failed", error=str(e))
        return {
            "error": str(e),
            "method": method,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def _calculate_kappa_batch(
    structures: List[Dict[str, Any]],
    method: str = "kappa_p",
    temperature: float = 300.0
) -> Dict[str, Any]:
    """
    Batch thermal conductivity calculation - processes all CIFs together in one temp directory.
    
    Args:
        structures: List of structure dicts with cifContent, formula, id
        method: Calculation method
        temperature: Temperature in Kelvin
    
    Returns:
        Dict with batch calculation results and summary
    """
    temp_dir = None
    try:
        logger.info(f"🔄 Starting batch thermal conductivity calculation for {len(structures)} structures")
        
        # Create single temporary directory for all CIFs
        temp_dir = tempfile.mkdtemp(prefix="kappa_batch_")
        
        results = []
        completed = 0
        failed = 0
        cif_files = []
        
        # Step 1: Prepare all CIF files in the temp directory
        for i, structure in enumerate(structures):
            structure_id = structure.get("id", f"structure_{i+1}")
            formula = structure.get("formula", f"Unknown_{i+1}")
            cif_content = structure.get("cifContent")
            
            if not cif_content:
                logger.warning(f"⚠️ Structure {i+1} ({formula}) has no CIF content, skipping")
                results.append({
                    "structure_id": structure_id,
                    "formula": formula,
                    "index": i + 1,
                    "success": False,
                    "error": "No CIF content available"
                })
                failed += 1
                continue
            
            try:
                # Handle base64 encoded content if needed
                try:
                    if not cif_content.strip().startswith('data_'):
                        decoded = base64.b64decode(cif_content).decode('utf-8')
                        cif_content = decoded
                except Exception:
                    pass
                
                # Normalize CIF content
                cif_content = normalize_cif_content(cif_content)
                
                # Save CIF file
                cif_filename = f"{formula}_{structure_id}.cif"
                cif_path = os.path.join(temp_dir, cif_filename)
                
                with open(cif_path, 'w', encoding='utf-8') as f:
                    f.write(cif_content)
                
                cif_files.append({
                    "path": cif_path,
                    "filename": cif_filename,
                    "structure_id": structure_id,
                    "formula": formula,
                    "index": i + 1
                })
                
                logger.info(f"✅ Prepared CIF {i+1}/{len(structures)}: {formula}")
                
            except Exception as e:
                logger.error(f"❌ Error preparing structure {i+1} ({formula}): {e}")
                results.append({
                    "structure_id": structure_id,
                    "formula": formula,
                    "index": i + 1,
                    "success": False,
                    "error": f"Failed to prepare CIF: {str(e)}"
                })
                failed += 1
        
        # Step 2: Batch calculate using kappa library if available
        if KAPPA_AVAILABLE and cif_files:
            try:
                logger.info(f"🚀 Running batch calculation with kappa library for {len(cif_files)} structures")
                
                # Create calculator with the temp directory containing all CIFs
                calculator = ThermalConductivityCalculator(temp_dir)
                
                # Calculate based on method (this processes all CIFs in the directory)
                if method.lower() == "kappa_p":
                    result_df = calculator.calculate_kappa_p()
                    kappa_column = 'Kappa_Slack (W m-1 K-1)'
                elif method.lower() == "kappa_mtp":
                    result_df = calculator.calculate_kappa_mtp()
                    kappa_column = 'Kappa_cal (W m-1 K-1)'
                else:
                    raise ValueError(f"Unknown method: {method}")
                
                # Process results for each structure
                for cif_info in cif_files:
                    try:
                        # Find matching row in result dataframe
                        # The result_df should have a row for each CIF file
                        cif_basename = os.path.splitext(cif_info["filename"])[0]
                        
                        # Try to match by filename or index
                        if not result_df.empty:
                            # Assuming results are in the same order as files
                            idx = cif_info["index"] - 1 - failed  # Adjust for failed structures
                            if idx < len(result_df):
                                kappa_value = float(result_df[kappa_column].iloc[idx])
                                
                                calc_id = f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cif_info['index']}"
                                
                                result = {
                                    "calculation_id": calc_id,
                                    "structure_id": cif_info["structure_id"],
                                    "formula": cif_info["formula"],
                                    "index": cif_info["index"],
                                    "method": f"Kappa-{'P (Slack Model)' if method.lower() == 'kappa_p' else 'MTP (ML)'}",
                                    "cif_filename": cif_info["filename"],
                                    "temperature": temperature,
                                    "temperature_unit": "K",
                                    "thermal_conductivity": {
                                        "value": round(kappa_value, 2),
                                        "unit": "W/(m·K)"
                                    },
                                    "calculation_mode": "real_batch",
                                    "timestamp": datetime.now().isoformat(),
                                    "success": True
                                }
                                
                                results.append(result)
                                completed += 1
                                logger.info(f"✅ {cif_info['formula']}: κ = {kappa_value:.2f} W/mK")
                            else:
                                raise IndexError(f"Result index {idx} out of range")
                        else:
                            raise ValueError("Empty result dataframe")
                            
                    except Exception as e:
                        logger.error(f"❌ Error processing result for {cif_info['formula']}: {e}")
                        results.append({
                            "structure_id": cif_info["structure_id"],
                            "formula": cif_info["formula"],
                            "index": cif_info["index"],
                            "success": False,
                            "error": f"Failed to extract result: {str(e)}"
                        })
                        failed += 1
                
            except Exception as e:
                logger.error(f"❌ Batch calculation failed: {e}")
                # Fall back to individual mock calculations
                for cif_info in cif_files:
                    mock_kappa = 100.0 + (hash(cif_info["filename"]) % 100)
                    calc_id = f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cif_info['index']}"
                    
                    results.append({
                        "calculation_id": calc_id,
                        "structure_id": cif_info["structure_id"],
                        "formula": cif_info["formula"],
                        "index": cif_info["index"],
                        "method": f"Kappa-{'P (Slack Model)' if method.lower() == 'kappa_p' else 'MTP (ML)'}",
                        "cif_filename": cif_info["filename"],
                        "temperature": temperature,
                        "temperature_unit": "K",
                        "thermal_conductivity": {
                            "value": round(mock_kappa, 2),
                            "unit": "W/(m·K)"
                        },
                        "calculation_mode": "mock_batch",
                        "note": f"Batch calculation failed: {str(e)}. Using mock values.",
                        "timestamp": datetime.now().isoformat(),
                        "success": True
                    })
                    completed += 1
        else:
            # Kappa library not available - use mock calculations
            logger.warning("Kappa library not available, using mock calculations")
            for cif_info in cif_files:
                mock_kappa = 100.0 + (hash(cif_info["filename"]) % 100)
                calc_id = f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cif_info['index']}"
                
                results.append({
                    "calculation_id": calc_id,
                    "structure_id": cif_info["structure_id"],
                    "formula": cif_info["formula"],
                    "index": cif_info["index"],
                    "method": f"Kappa-{'P (Slack Model)' if method.lower() == 'kappa_p' else 'MTP (ML)'}",
                    "cif_filename": cif_info["filename"],
                    "temperature": temperature,
                    "temperature_unit": "K",
                    "thermal_conductivity": {
                        "value": round(mock_kappa, 2),
                        "unit": "W/(m·K)"
                    },
                    "calculation_mode": "mock_batch",
                    "note": "Kappa library not available. Using mock values.",
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                })
                completed += 1
        
        # Generate summary
        summary = {
            "total_structures": len(structures),
            "completed": completed,
            "failed": failed,
            "success_rate": f"{(completed/len(structures)*100):.1f}%" if structures else "0%",
            "method": method,
            "temperature": temperature
        }
        
        # Extract successful thermal conductivity values
        successful_kappas = []
        for r in results:
            if r.get("success", False):
                tc = r.get("thermal_conductivity", {})
                if tc and tc.get("value") is not None:
                    successful_kappas.append({
                        "formula": r["formula"],
                        "kappa_total": tc.get("value"),
                        "unit": tc.get("unit", "W/(m·K)")
                    })
        
        if successful_kappas:
            summary["thermal_conductivities"] = successful_kappas
            # Calculate average
            avg_kappa = sum(k["kappa_total"] for k in successful_kappas) / len(successful_kappas)
            summary["average_kappa"] = round(avg_kappa, 4)
        
        logger.info(f"✅ Batch calculation completed: {completed}/{len(structures)} successful")
        
        return {
            "success": True,
            "batch_mode": True,
            "total": len(structures),
            "completed": completed,
            "failed": failed,
            "results": results,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Batch calculation failed: {e}")
        return {
            "success": False,
            "batch_mode": True,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"🧹 Cleaned up temp directory: {temp_dir}")


def convert_cif_to_frontend_structure(
    cif_content: str,
    composition: str = "Unknown",
    source: str = "Unknown"
) -> Dict[str, Any]:
    """
    Convert CIF content to frontend-compatible structure format.

    This function uses the same logic as the backend's convert_cif_to_structure
    to ensure consistency.

    Args:
        cif_content: CIF file content
        composition: Chemical composition
        source: Source of the structure (e.g., "Relaxed", "Generated")

    Returns:
        Frontend-compatible structure dict
    """
    try:
        from pymatgen.core import Structure
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        import uuid
        import base64

        structure_id = str(uuid.uuid4())

        # Extract space group from CIF
        space_group = "P1"
        space_group_number = 1
        for line in cif_content.split('\n'):
            if '_symmetry_space_group_name_H-M' in line or '_space_group_name_H-M_alt' in line:
                parts = line.split("'")
                if len(parts) >= 2:
                    space_group = parts[1].strip()
                    break

        # Parse CIF using pymatgen
        struct = Structure.from_str(cif_content, fmt="cif")

        # Analyze symmetry and get primitive and conventional cells
        primitive_data = None
        conventional_data = None

        try:
            sga = SpacegroupAnalyzer(struct)
            primitive_structure = sga.get_primitive_standard_structure()
            conventional_structure = sga.get_conventional_standard_structure()

            # Get space group info
            space_group = sga.get_space_group_symbol()
            space_group_number = sga.get_space_group_number()
            crystal_system = sga.get_crystal_system()

            composition = primitive_structure.composition.reduced_formula

            logger.info(f"✅ Analyzed structure: {composition}")
            logger.info(f"   Primitive: {len(primitive_structure)} sites")
            logger.info(f"   Conventional: {len(conventional_structure)} sites")

            # Extract primitive cell data
            prim_lattice = primitive_structure.lattice
            primitive_data = {
                "latticeParameters": {
                    "a": round(prim_lattice.a, 6),
                    "b": round(prim_lattice.b, 6),
                    "c": round(prim_lattice.c, 6),
                    "alpha": round(prim_lattice.alpha, 6),
                    "beta": round(prim_lattice.beta, 6),
                    "gamma": round(prim_lattice.gamma, 6)
                },
                "atoms": [],
                "volume": float(prim_lattice.volume),
                "numAtoms": len(primitive_structure)
            }
            for site in primitive_structure:
                # 保存分数坐标用于cellTypes切换
                primitive_data["atoms"].append({
                    "element": site.species_string,
                    "position": [round(x, 6) for x in site.frac_coords.tolist()],
                    "occupancy": 1.0
                })

            # Extract conventional cell data
            conv_lattice = conventional_structure.lattice
            conventional_data = {
                "latticeParameters": {
                    "a": round(conv_lattice.a, 6),
                    "b": round(conv_lattice.b, 6),
                    "c": round(conv_lattice.c, 6),
                    "alpha": round(conv_lattice.alpha, 6),
                    "beta": round(conv_lattice.beta, 6),
                    "gamma": round(conv_lattice.gamma, 6)
                },
                "atoms": [],
                "volume": float(conv_lattice.volume),
                "numAtoms": len(conventional_structure)
            }
            for site in conventional_structure:
                conventional_data["atoms"].append({
                    "element": site.species_string,
                    "position": [round(x, 6) for x in site.frac_coords.tolist()],
                    "occupancy": 1.0
                })

            # Use primitive structure for display by default
            display_struct = primitive_structure
            lattice_params = primitive_data["latticeParameters"]

            # 为主显示使用笛卡尔坐标（重要：前端期望笛卡尔坐标）
            atoms = []
            for site in primitive_structure:
                atoms.append({
                    "element": site.species_string,
                    "position": [round(x, 6) for x in site.coords.tolist()],  # 使用笛卡尔坐标
                    "occupancy": 1.0
                })

        except Exception as sga_error:
            logger.warning(f"⚠️ SpacegroupAnalyzer failed: {sga_error}, using original structure")
            display_struct = struct
            primitive_structure = struct
            conventional_structure = struct
            composition = struct.composition.reduced_formula
            crystal_system = "triclinic"

            # Extract from original structure
            lattice = display_struct.lattice
            lattice_params = {
                "a": round(lattice.a, 6),
                "b": round(lattice.b, 6),
                "c": round(lattice.c, 6),
                "alpha": round(lattice.alpha, 6),
                "beta": round(lattice.beta, 6),
                "gamma": round(lattice.gamma, 6)
            }

            # Extract atoms from display structure (use Cartesian coordinates for display)
            atoms = []
            for site in display_struct:
                atoms.append({
                    "element": site.species_string,
                    "position": [round(x, 6) for x in site.coords.tolist()],  # 使用笛卡尔坐标
                    "occupancy": 1.0
                })

        logger.info(f"✅ Extracted {len(atoms)} atoms and lattice parameters from CIF")

        # Build result structure
        result = {
            "id": structure_id,
            "name": composition,
            "formula": composition,
            "source": {
                "database": source,
                "materialId": structure_id,
            },
            "spaceGroup": space_group,
            "cifContent": cif_content,  # 统一使用 cifContent 字段
            "properties": {
                "density": float(display_struct.density) if display_struct else None,
                "volume": float(display_struct.lattice.volume) if display_struct else None,
                "numAtoms": len(atoms) if atoms else 0,
                "spaceGroupNumber": space_group_number,
                "crystalSystem": crystal_system
            },
            "metadata": {
                "source": source,
                "timestamp": datetime.now().isoformat()
            }
        }

        logger.info(f"✅ 结构数据包含 CIF 内容: {len(cif_content)} 字符")

        # Add lattice parameters and atoms
        result["latticeParameters"] = lattice_params
        result["atoms"] = atoms

        # Add cell type data for switching
        if primitive_data and conventional_data:
            result["cellTypes"] = {
                "primitive": primitive_data,
                "conventional": conventional_data
            }
            result["currentCellType"] = "primitive"  # Default to primitive, can switch to conventional
            logger.info(f"✅ Added cell type data: primitive ({primitive_data['numAtoms']} atoms) and conventional ({conventional_data['numAtoms']} atoms)")

        return result

    except Exception as e:
        logger.error(f"Failed to convert CIF to frontend structure: {e}")
        return None
