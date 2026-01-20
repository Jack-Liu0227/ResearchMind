"""
Structure Data Converter

Converts crystal structure data from various sources (MCP tools, CIF files, etc.)
to a unified frontend format.
"""

import base64
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class StructureConverter:
    """Convert structure data to unified frontend format"""
    
    @staticmethod
    def convert_cif_to_structure(
        cif_content: str,
        name: str,
        composition: str,
        source: str = "Database"
    ) -> Optional[Dict[str, Any]]:
        """
        Convert CIF content to frontend structure format

        Args:
            cif_content: CIF file content (can be None for structures without CIF)
            name: Structure name
            composition: Chemical composition
            source: Data source (MP/OQMD/COD/AFLOW/Generated/Upload)

        Returns:
            Structure dict in frontend format, or None if conversion fails
        """
        try:
            from pymatgen.core import Structure
            from io import StringIO

            # Handle None or empty CIF content
            if not cif_content:
                logger.warning(f"No CIF content provided for {name}, skipping conversion")
                return None

            # 关键修复：验证CIF内容的完整性
            logger.info(f"🔍 Processing CIF for {name}: {len(cif_content)} characters")
            if len(cif_content) < 100:
                logger.warning(f"⚠️ CIF content seems too short ({len(cif_content)} chars), may be truncated")

            # 检查CIF内容是否包含必要的关键字
            required_keywords = ['data_', '_cell_length_a']
            missing_keywords = [kw for kw in required_keywords if kw not in cif_content]
            if missing_keywords:
                logger.warning(f"⚠️ CIF content missing keywords: {missing_keywords}")
                # Don't raise error, let pymatgen try to parse or fail gracefully
                # raise ValueError(f"Invalid CIF: missing keywords {missing_keywords}")

            structure_id = str(uuid.uuid4())
            
            # Extract space group from CIF
            space_group = StructureConverter._extract_space_group(cif_content)
            
            # Note: We don't generate base64 here to save space
            # CIF content is stored in metadata.cifData for download/export only

            # Parse CIF to extract lattice parameters and atoms using pymatgen
            lattice_params = None
            atoms = []
            primitive_structure = None
            conventional_structure = None
            primitive_data = None
            conventional_data = None
            # Ensure display_struct is always defined to avoid UnboundLocalError
            display_struct = None

            # Try to auto-detect format if pymatgen fails
            try:
                from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

                # 详细日志，帮助定位解析问题
                logger.info(f"🔍 Attempting to parse CIF with pymatgen...")
                logger.info(f"   CIF content length: {len(cif_content)} characters")
                logger.info(f"   CIF content starts with: {cif_content[:100]}")

                try:
                    # Try explicit CIF format first
                    struct = Structure.from_str(cif_content, fmt="cif")
                    logger.info(f"✅ CIF parsed successfully as CIF format")
                except Exception as cif_error:
                    # 🔧 修复：如果不是标准CIF，尝试自动检测格式（支持POSCAR等）
                    # Check if it looks like a POSCAR
                    if "Direct" in cif_content or "Cartesian" in cif_content or any(x in cif_content.splitlines()[0] for x in ["POSCAR", "CONTCAR", "SrTiO3", "system"]):
                        logger.info("ℹ️ Content looks like POSCAR/VASP format, trying auto-detection")
                        try:
                            struct = Structure.from_str(cif_content) # Auto-detect
                            logger.info(f"✅ Structure parsed successfully with auto-detection")
                        except Exception as auto_error:
                            logger.warning(f"⚠️ Auto-detection failed: {auto_error}")
                            raise cif_error # Re-raise original error if auto-detect fails
                    else:
                        raise cif_error

                # Analyze symmetry and get primitive and conventional cells
                try:
                    sga = SpacegroupAnalyzer(struct)
                    primitive_structure = sga.get_primitive_standard_structure()
                    conventional_structure = sga.get_conventional_standard_structure()
                    
                    # 🔧 修复：使用 SpacegroupAnalyzer 获取的空间群覆盖从 CIF 提取的值
                    # 这样可以确保即使 CIF 文件中没有空间群信息，也能正确显示
                    try:
                        space_group = sga.get_space_group_symbol()
                        logger.info(f"✅ Space group from analyzer: {space_group}")
                    except Exception as sg_error:
                        logger.warning(f"⚠️ Could not get space group symbol: {sg_error}")
                        # 保留从 CIF 提取的值

                    # Get refined formula
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
                    composition = struct.composition.reduced_formula

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

                    # Extract atoms from display structure (use Cartesian coordinates)
                    for site in display_struct:
                        atoms.append({
                            "element": site.species_string,
                            "position": [round(x, 6) for x in site.coords.tolist()],  # 使用笛卡尔坐标
                            "occupancy": 1.0
                        })

                logger.info(f"✅ Extracted {len(atoms)} atoms and lattice parameters from CIF")

            except Exception as parse_error:
                logger.warning(f"⚠️ Could not parse CIF with pymatgen: {parse_error}")
                # Continue without lattice/atoms data

            # Get space group number and crystal system if available
            space_group_number = None
            crystal_system = None
            if primitive_structure is not None or display_struct is not None:
                try:
                    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
                    sga_temp = SpacegroupAnalyzer(display_struct if display_struct is not None else primitive_structure)
                    space_group_number = sga_temp.get_space_group_number()
                    crystal_system = sga_temp.get_crystal_system()
                except Exception as e:
                    logger.warning(f"⚠️ Could not get space group number: {e}")

            result = {
                "id": structure_id,
                "name": name,
                "formula": composition,
                "source": {
                    "database": source,
                    "materialId": structure_id,
                },
                "spaceGroup": space_group,
                "cifContent": cif_content,  # 统一使用 cifContent 字段
                "properties": {
                    "density": float(display_struct.density) if display_struct is not None else None,
                    "volume": float(display_struct.lattice.volume) if display_struct is not None else None,
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

            # Add lattice parameters and atoms if successfully extracted
            if lattice_params:
                result["latticeParameters"] = lattice_params
            if atoms:
                result["atoms"] = atoms

            # Add cell type data for switching
            if primitive_data and conventional_data:
                result["cellTypes"] = {
                    "primitive": primitive_data,
                    "conventional": conventional_data
                }
                result["currentCellType"] = "primitive"  # Default to primitive
                logger.info(f"✅ Added cell type data: primitive ({primitive_data['numAtoms']} atoms) and conventional ({conventional_data['numAtoms']} atoms)")

            return result

        except Exception as e:
            # Fallback: build minimal structure without pymatgen
            logger.warning(f"⚠️ CIF parse failed or pymatgen unavailable, using fallback parser: {e}")

            # Try to extract formula from CIF text
            try:
                import re
                formula = composition
                m = re.search(r"^_chemical_formula_sum\s+(.+)$", cif_content, flags=re.MULTILINE)
                if m:
                    formula = m.group(1).strip().strip('"\'')
                else:
                    m2 = re.search(r"^data_([A-Za-z0-9_]+)$", cif_content, flags=re.MULTILINE)
                    if m2:
                        formula = m2.group(1).strip()
            except Exception:
                formula = composition or name or "N/A"

            # Extract lattice parameters if present
            lattice_params = None
            try:
                import re
                def find_float(tag: str) -> Optional[float]:
                    mm = re.search(rf"^{tag}\\s+([0-9]+(?:\\.[0-9]+)?)", cif_content, flags=re.MULTILINE)
                    return float(mm.group(1)) if mm else None

                a = find_float("_cell_length_a")
                b = find_float("_cell_length_b")
                c = find_float("_cell_length_c")
                alpha = find_float("_cell_angle_alpha")
                beta = find_float("_cell_angle_beta")
                gamma = find_float("_cell_angle_gamma")

                if all(v is not None for v in [a, b, c, alpha, beta, gamma]):
                    lattice_params = {
                        "a": a, "b": b, "c": c,
                        "alpha": alpha, "beta": beta, "gamma": gamma
                    }
            except Exception:
                lattice_params = None

            # Minimal result; atoms left empty so UI can still show metadata
            minimal = {
                "id": str(uuid.uuid4()),
                "name": name,
                "formula": formula,
                "source": {
                    "database": source,
                    "materialId": name or "N/A",
                },
                "spaceGroup": StructureConverter._extract_space_group(cif_content),
                "cifContent": cif_content,
                "properties": {
                    "density": None,
                    "volume": None,
                    "numAtoms": 0,
                    "spaceGroupNumber": None,
                    "crystalSystem": None,
                },
                "metadata": {
                    "source": source,
                    "timestamp": datetime.now().isoformat(),
                },
                "atoms": [],
            }
            if lattice_params:
                minimal["latticeParameters"] = lattice_params

            logger.info("✅ Fallback structure created (no atoms). Frontend can still display metadata and allow CIF download.")
            return minimal
    
    @staticmethod
    def _extract_space_group(cif_content: str) -> str:
        """Extract space group from CIF content"""
        try:
            for line in cif_content.split('\n'):
                if '_space_group_name_H-M' in line or '_symmetry_space_group_name_H-M' in line:
                    parts = line.split()
                    if len(parts) > 1:
                        return ' '.join(parts[1:]).strip('"\'')
            return "N/A"
        except Exception as e:
            logger.warning(f"Failed to extract space group: {e}")
            return "N/A"

    @staticmethod
    def _infer_source_database(data: Dict[str, Any], default: str) -> str:
        if default and default != "Unknown":
            return default

        for key in ("database", "db"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value

        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            for key in ("database", "source"):
                value = metadata.get(key)
                if isinstance(value, str) and value:
                    return value

        for filename_key in ("cif_file_path", "cifFilename"):
            filename = data.get(filename_key)
            if isinstance(filename, str) and filename:
                name = filename.split("\\")[-1].split("/")[-1]
                if name.startswith("MP_"):
                    return "MP"
                if name.startswith("OQMD_"):
                    return "OQMD"
                if name.startswith("COD_"):
                    return "COD"
                if name.startswith("AFLOW_"):
                    return "AFLOW"

        material_id = data.get("material_id") or data.get("materialId")
        if isinstance(material_id, str) and material_id.startswith("mp-"):
            return "MP"
        if data.get("aflow_id") or data.get("auid"):
            return "AFLOW"
        if data.get("cod_id"):
            return "COD"
        if data.get("entry_id") or data.get("icsd_id"):
            return "OQMD"

        # 🔧 修复：即使无法确定具体数据库，也返回通用的Database而不是Unknown
        return default if default and default != "Unknown" else "Database"
    
    @staticmethod
    def standardize_structure_data(data: Dict[str, Any], source_type: str = "Database") -> Dict[str, Any]:
        """
        Standardize structure data from different sources

        Ensures all structure data has:
        - Unified source field format: {database: "...", materialId: "..."}
        - cifData in metadata.cifData
        - Consistent field names

        Args:
            data: Raw structure data
            source_type: Source type (MP/OQMD/COD/AFLOW/Generated/Upload)

        Returns:
            Standardized structure data
        """
        try:
            # Create a copy to avoid modifying original
            standardized = data.copy()

            # Log original source for debugging
            original_source = standardized.get("source")
            logger.info(f"🔍 Standardizing structure - Original source: {original_source}, source_type param: {source_type}")

            resolved_source = StructureConverter._infer_source_database(standardized, source_type)

            # Standardize source field
            if "source" not in standardized or not isinstance(standardized["source"], dict):
                logger.info(f"📝 Creating new source field with database={resolved_source}")
                standardized["source"] = {
                    "database": resolved_source,
                    "materialId": standardized.get("id", "unknown")
                }
            elif "database" not in standardized["source"]:
                logger.info(f"📝 Adding database={resolved_source} to existing source")
                standardized["source"]["database"] = resolved_source
            else:
                logger.info(f"✅ Keeping existing source.database={standardized['source']['database']}")
            
            # Ensure metadata exists
            if "metadata" not in standardized:
                standardized["metadata"] = {}
            
            # Ensure cifContent is available (unified field name)
            # Priority: cifContent > cif_structure > cif_file_content > cifData
            cif_data = (
                standardized.get("cifContent") or
                standardized.get("cif_structure") or
                standardized.get("cif_file_content") or
                standardized.get("metadata", {}).get("cifData") or
                ""
            )

            # Set unified cifContent field
            if cif_data:
                standardized["cifContent"] = cif_data
                # Also keep in metadata for backward compatibility
                standardized["metadata"]["cifData"] = cif_data

            # 🆕 关键修复：保留 cif_file_path 字段（用于模拟计算）
            cif_file_path = data.get("cif_file_path")
            if cif_file_path:
                standardized["cif_file_path"] = cif_file_path
                logger.info(f"📁 Preserving cif_file_path: {cif_file_path}")

            # 🆕 保留 cifFilename 字段
            cif_filename = data.get("cifFilename")
            if cif_filename:
                standardized["cifFilename"] = cif_filename

            # Ensure properties field exists
            if "properties" not in standardized:
                standardized["properties"] = {}

            # 🔧 修复：统一 formula 字段（前端期望 formula 字段）
            # 不同数据库使用不同的字段名：MP用formula_pretty，OQMD用composition，COD用chemical_formula
            current_formula = standardized.get("formula", "")
            # 如果formula不存在、为空、或是无效值（N/A, Unknown等），尝试从其他字段提取
            if not current_formula or current_formula in ("N/A", "Unknown", "unknown") or current_formula.startswith("Structure_"):
                formula = (
                    standardized.get("formula_pretty") or
                    standardized.get("composition") or
                    standardized.get("chemical_formula") or
                    standardized.get("name") or
                    f"Structure_{standardized.get('id', 'N/A')[:8]}"
                )
                standardized["formula"] = formula
                logger.info(f"📝 Unified formula field: {current_formula} -> {formula}")

            # Preserve important properties if they exist in metadata or top-level
            for prop_key in ["density", "volume", "bandGap", "energyAboveHull", "numAtoms", "spaceGroupNumber", "crystalSystem"]:
                # Check if property exists in metadata but not in properties
                if prop_key in standardized.get("metadata", {}) and prop_key not in standardized["properties"]:
                    standardized["properties"][prop_key] = standardized["metadata"][prop_key]
                # Check if property exists at top level but not in properties
                elif prop_key in standardized and prop_key not in standardized["properties"]:
                    standardized["properties"][prop_key] = standardized[prop_key]

            # Add timestamp if missing
            if "timestamp" not in standardized["metadata"]:
                standardized["metadata"]["timestamp"] = datetime.now().isoformat()

            return standardized
            
        except Exception as e:
            logger.error(f"Failed to standardize structure data: {e}")
            return data
    
    @staticmethod
    def extract_structures_from_tool_result(result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract structure data from MCP tool result

        Handles various result formats:
        - frontend_structures (list)
        - structures (list)
        - structure (single)
        - cif_content/cif_contents
        - AFLOW specific format

        Args:
            result: Tool result data

        Returns:
            List of structure dicts
        """
        structures = []
        skip_standardization = False  # Flag to skip standardization for already-standardized structures

        try:
            logger.info(f"🔍 Extracting structures from tool result")
            logger.info(f"🔍 Result type: {type(result)}")
            logger.info(f"🔍 Result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")

            # 🔧 修复问题 1: 跳过热导率计算结果中的结构提取
            # 热导率计算结果不应该包含结构数据，即使包含也不应该提取
            if isinstance(result, dict):
                # 检测热导率计算结果的特征
                is_kappa_result = (
                    result.get("batch_mode") is True or  # 批量热导率计算
                    "thermal_conductivity" in result or  # 单个热导率计算
                    "kappa_total" in result or  # 热导率值
                    result.get("calculation_mode") in ["real", "real_batch", "mock_batch"]  # 计算模式
                )

                if is_kappa_result:
                    logger.info(f"🔧 Detected thermal conductivity calculation result, skipping structure extraction")
                    return []

            # Method 1: frontend_structures field (preferred)
            if "frontend_structures" in result and isinstance(result["frontend_structures"], list):
                logger.info(f"✅ [structure_converter] Found frontend_structures: {len(result['frontend_structures'])} items")
                # Process each frontend structure to ensure it has complete data
                for i, struct in enumerate(result["frontend_structures"]):
                    if isinstance(struct, dict):
                        # 检查是否已经解析过（有完整的 latticeParameters 和 atoms）
                        has_lattice = "latticeParameters" in struct and isinstance(struct["latticeParameters"], dict)
                        has_atoms = "atoms" in struct and isinstance(struct["atoms"], list) and len(struct["atoms"]) > 0
                        has_space_group = "spaceGroup" in struct and struct["spaceGroup"]
                        is_already_analyzed = has_lattice and has_atoms and has_space_group

                        # 调试日志
                        logger.info(f"🔍 检查结构 {i+1}: {struct.get('formula', 'Unknown')}")
                        logger.info(f"   has_lattice: {has_lattice}")
                        logger.info(f"   has_atoms: {has_atoms} (count: {len(struct.get('atoms', []))})")
                        logger.info(f"   has_space_group: {has_space_group} ({struct.get('spaceGroup', 'None')})")
                        logger.info(f"   is_already_analyzed: {is_already_analyzed}")

                        # 如果已经解析过，直接使用
                        if is_already_analyzed:
                            logger.info(f"✅ 结构 {i+1} 已解析，直接使用: {struct.get('formula', 'Unknown')}")
                            structures.append(struct)
                            continue

                        # 检查是否有 CIF 内容需要分析
                        cif_content = struct.get("cifContent") or struct.get("metadata", {}).get("cifData")
                        if cif_content:
                            # 使用 SpacegroupAnalyzer 分析结构
                            analyzed = StructureConverter.convert_cif_to_structure(
                                cif_content,
                                struct.get("name", struct.get("formula", f"structure_{i+1}")),
                                struct.get("formula", "Unknown"),
                                struct.get("source", {}).get("database", "Generated")
                            )
                            if analyzed:
                                # 保留原始结构中的额外字段（但不覆盖分析后的关键字段）
                                # 关键字段：formula, spaceGroup, latticeParameters, atoms, properties
                                preserved_fields = {}
                                for k, v in struct.items():
                                    # 只保留非关键字段
                                    if k not in ['formula', 'spaceGroup', 'latticeParameters', 'atoms', 'properties', 'cifContent'] and v is not None:
                                        preserved_fields[k] = v

                                # 🆕 确保 cif_file_path 被保留
                                if 'cif_file_path' in preserved_fields:
                                    logger.info(f"📁 Preserving cif_file_path in analyzed structure: {preserved_fields['cif_file_path']}")

                                # 合并：分析后的数据优先，只添加额外字段
                                analyzed.update(preserved_fields)

                                logger.info(f"✅ 重新分析结构 {i+1}: {analyzed.get('formula', 'Unknown')}")
                                logger.info(f"   原子数: {len(analyzed.get('atoms', []))}")
                                logger.info(f"   空间群: {analyzed.get('spaceGroup', 'Unknown')}")

                                structures.append(analyzed)
                            else:
                                # Use original if analysis failed
                                logger.warning(f"⚠️ 结构 {i+1} 分析失败，使用原始数据")
                                structures.append(struct)
                        else:
                            # No CIF content, use as-is
                            logger.info(f"ℹ️ 结构 {i+1} 无 CIF 内容，使用原始数据")
                            structures.append(struct)
                    else:
                        structures.append(struct)
                logger.info(f"✅ Found {len(result['frontend_structures'])} structures in frontend_structures")
                # frontend_structures are already standardized, skip standardization step
                skip_standardization = True

            # Method 1.5: frontend_structure field (singular)
            elif "frontend_structure" in result and isinstance(result["frontend_structure"], dict):
                logger.info("🔍 Found singular frontend_structure")
                struct = result["frontend_structure"]
                # Check for completeness
                has_lattice = "latticeParameters" in struct and isinstance(struct["latticeParameters"], dict)
                has_atoms = "atoms" in struct and isinstance(struct["atoms"], list) and len(struct["atoms"]) > 0
                
                if has_lattice and has_atoms:
                    structures.append(struct)
                    skip_standardization = True
                    logger.info(f"✅ Extracted singular frontend_structure: {struct.get('formula', 'Unknown')}")

            # Method 2: structures field
            elif "structures" in result and isinstance(result["structures"], list):
                # Check database type for format-specific processing
                database_type = result.get("database", "Unknown")
                
                for i, struct in enumerate(result["structures"]):
                    if isinstance(struct, dict):
                        # Handle all formats with CIF content (MP/OQMD/COD/AFLOW)
                        cif_content = struct.get("cifContent")
                        
                        # Only try to convert if CIF content exists and is not None
                        if cif_content:
                            # Convert from MP/OQMD/COD format to frontend format
                            converted = StructureConverter.convert_cif_to_structure(
                                cif_content,
                                struct.get("material_id", struct.get("name", f"structure_{i+1}")),
                                struct.get("formula_pretty", struct.get("composition", "Unknown")),
                                database_type
                            )
                            if converted:
                                # 🆕 关键修复：保留原始 struct 中的 cif_file_path
                                if struct.get("cif_file_path"):
                                    converted["cif_file_path"] = struct["cif_file_path"]
                                    logger.info(f"📁 Preserved cif_file_path: {struct['cif_file_path']}")
                                if struct.get("cifFilename"):
                                    converted["cifFilename"] = struct["cifFilename"]
                                
                                # Add additional metadata from source database
                                if "metadata" not in converted:
                                    converted["metadata"] = {}
                                
                                # MP specific metadata
                                if database_type == "MP":
                                    converted["metadata"].update({
                                        "material_id": struct.get("material_id"),
                                        "band_gap": struct.get("band_gap"),
                                        "energy_above_hull": struct.get("energy_above_hull"),
                                        "is_stable": struct.get("is_stable"),
                                        "symmetry": struct.get("symmetry")
                                    })
                                
                                # OQMD specific metadata
                                elif database_type == "OQMD":
                                    converted["metadata"].update({
                                        "entry_id": struct.get("material_id"),
                                        "icsd_id": struct.get("icsd_id"),
                                        "stability": struct.get("structure", {}).get("stability")
                                    })
                                
                                # COD specific metadata
                                elif database_type == "COD":
                                    converted["metadata"].update({
                                        "cod_id": struct.get("cod_id"),
                                        "mineral_name": struct.get("mineral_name"),
                                        "source_doi": struct.get("source_doi")
                                    })
                                
                                # AFLOW specific metadata
                                elif database_type == "AFLOW":
                                    converted["metadata"].update({
                                        "aflow_id": struct.get("aflow_id"),
                                        "compound": struct.get("compound"),
                                        "structure_info": struct.get("structure")
                                    })
                                
                                # Add properties to properties field (not metadata)
                                if "properties" not in converted:
                                    converted["properties"] = {}
                                
                                # Common properties
                                for prop_key, struct_key in [
                                    ("volume", "volume"),
                                    ("density", "density"), 
                                    ("bandGap", "band_gap"),
                                    ("energyAboveHull", "energy_above_hull")
                                ]:
                                    if struct.get(struct_key) is not None:
                                        converted["properties"][prop_key] = struct.get(struct_key)
                                
                                structures.append(converted)
                        else:
                            # 🔧 修复：没有 CIF 内容的结构不应该被添加
                            # 这些结构无法正确显示（缺少晶格参数、原子位置等关键信息）
                            logger.warning(f"⚠️ Structure {i+1} has no CIF content, skipping")
                            # 如果这是一个已经格式化的结构（有 latticeParameters 和 atoms），可以保留
                            if struct.get("latticeParameters") and struct.get("atoms"):
                                logger.info(f"✅ Structure {i+1} has lattice and atoms, keeping")
                                structures.append(struct)
                    else:
                        logger.warning(f"⚠️ Structure {i+1} is not a dict, skipping")
                logger.info(f"✅ Found {len(structures)} structures in structures field")
            
            # Method 3: single structure field
            # 🔧 修复：跳过OQMD/COD等数据库格式中的嵌套structure字段（只是元数据）
            # 只处理真正的完整结构对象（有latticeParameters和atoms的）
            elif "structure" in result and isinstance(result["structure"], dict):
                struct = result["structure"]
                # 检查是否是完整的结构对象（有latticeParameters和atoms）
                # 而不是数据库格式中的元数据结构（只有space_group, unit_cell等）
                has_lattice_params = "latticeParameters" in struct
                has_atoms = "atoms" in struct and isinstance(struct["atoms"], list)
                is_metadata_only = "space_group" in struct or "unit_cell" in struct
                
                if has_lattice_params and has_atoms and not is_metadata_only:
                    # 这是一个完整的结构，可以使用
                    structures.append(struct)
                    logger.info("✅ Found 1 complete structure in structure field")
                else:
                    # 这只是元数据，跳过（真正的结构应该在structures数组或其他地方）
                    logger.info("⏭️ Skipping metadata-only structure field (not a complete structure)")
            
            # Method 4: CIF content
            elif "cif_content" in result or "cif_contents" in result:
                cif_data = result.get("cif_content") or result.get("cif_contents")
                if isinstance(cif_data, str):
                    cif_data = [cif_data]

                # Determine source type
                source_db = "Unknown"
                if isinstance(result.get("source"), dict):
                    source_db = result["source"].get("database", "Unknown")
                elif isinstance(result.get("source"), str):
                    source_db = result["source"]

                for i, cif_content in enumerate(cif_data):
                    if cif_content and str(cif_content).strip():
                        structure = StructureConverter.convert_cif_to_structure(
                            str(cif_content),
                            f"structure_{i+1}",
                            result.get("composition", "Unknown"),
                            source_db
                        )
                        if structure:
                            structures.append(structure)

                logger.info(f"✅ Converted {len(structures)} structures from CIF content")
            else:
                logger.warning(f"⚠️ No structures found in tool result")
                logger.warning(f"⚠️ Available keys: {list(result.keys())}")

            # Standardize all structures (skip if already standardized)
            if structures and not skip_standardization:
                source_type = StructureConverter._determine_source_type(result)
                logger.info(f"🔍 Determined source_type: {source_type} from result keys: {list(result.keys())}")

                standardized_structures = []
                for i, s in enumerate(structures):
                    logger.info(f"🔍 Standardizing structure {i+1}/{len(structures)}: {s.get('formula', 'Unknown')}")
                    standardized = StructureConverter.standardize_structure_data(s, source_type)
                    standardized_structures.append(standardized)
                    logger.info(f"✅ Structure {i+1} final source: {standardized.get('source', {}).get('database', 'N/A')}")

                structures = standardized_structures
                logger.info(f"📊 Total structures extracted: {len(structures)}")
            elif structures and skip_standardization:
                logger.info(f"📊 Total structures extracted: {len(structures)} (already standardized, skipped standardization step)")

            # 🔧 去重：基于 material_id 或 id 去除重复结构
            if structures:
                seen_ids = set()
                unique_structures = []
                for struct in structures:
                    # 尝试多个可能的 ID 字段
                    struct_id = (
                        struct.get("id") or
                        struct.get("source", {}).get("materialId") or
                        struct.get("material_id") or
                        struct.get("metadata", {}).get("entry_id") or
                        struct.get("metadata", {}).get("material_id") or
                        # 如果没有 ID，使用 formula + volume 作为唯一标识
                        f"{struct.get('formula', 'Unknown')}_{struct.get('properties', {}).get('volume', '')}"
                    )
                    
                    if struct_id not in seen_ids:
                        seen_ids.add(struct_id)
                        unique_structures.append(struct)
                    else:
                        logger.info(f"🔄 Skipping duplicate structure: {struct.get('formula', 'Unknown')} (ID: {struct_id})")
                
                removed_count = len(structures) - len(unique_structures)
                if removed_count > 0:
                    logger.info(f"✂️ Removed {removed_count} duplicate structures, {len(unique_structures)} unique structures remain")
                structures = unique_structures

        except Exception as e:
            logger.error(f"❌ Failed to extract structures from tool result: {e}", exc_info=True)

        return structures
    
    @staticmethod
    def _determine_source_type(result: Dict[str, Any]) -> str:
        """Determine source type from tool result"""
        # Check source field
        if "source" in result:
            if isinstance(result["source"], dict):
                return result["source"].get("database", "Unknown")
            elif isinstance(result["source"], str):
                return result["source"]
        
        # Check database field
        if "database" in result:
            return result["database"]
        
        # Check query_info
        if "query_info" in result and isinstance(result["query_info"], dict):
            return result["query_info"].get("database", "Unknown")
        
        # Check tool name
        tool_name = result.get("tool_name", "")
        if "mp" in tool_name.lower() or "materials_project" in tool_name.lower():
            return "MP"
        elif "oqmd" in tool_name.lower():
            return "OQMD"
        elif "cod" in tool_name.lower():
            return "COD"
        elif "aflow" in tool_name.lower():
            return "AFLOW"
        elif "generate" in tool_name.lower() or "crystallm" in tool_name.lower():
            return "Generated"
        
        return "Unknown"
    

    

    
    @staticmethod
    def mark_as_uploaded(structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mark a structure as uploaded by user

        Args:
            structure: Structure data

        Returns:
            Structure with Upload source marker
        """
        logger.info(f"📤 Marking structure as uploaded: {structure.get('formula', 'Unknown')}")
        logger.info(f"🔍 Original source before marking: {structure.get('source')}")

        structure = structure.copy()
        structure["source"] = {
            "database": "Upload",
            "materialId": structure.get("id", str(uuid.uuid4())),
            "uploadedAt": datetime.now().isoformat()
        }
        if "metadata" not in structure:
            structure["metadata"] = {}
        structure["metadata"]["source"] = "Upload"
        structure["metadata"]["uploadedAt"] = datetime.now().isoformat()

        logger.info(f"✅ Structure marked as Upload: {structure['source']}")
        logger.info(f"✅ Final structure source field: {structure.get('source', {}).get('database')}")
        logger.info(f"✅ Final structure metadata source: {structure.get('metadata', {}).get('source')}")

        return structure

