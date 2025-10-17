"""
Materials Database MCP Server
Provides tools for searching materials databases like Materials Project, OQMD, JARVIS.
Enhanced with frontend integration and structure generation support.
"""
import os
import math
import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import requests # COD
import qmpy_rester as qr # OQMD
from aflow import search, K # AFLOW
from mp_api.client import MPRester # MP
from pymatgen.io.cif import CifWriter  # For CIF export
from pymatgen.core import Structure

import httpx
from fastmcp import FastMCP
import structlog
from dotenv import load_dotenv
load_dotenv(override=True)

logger = structlog.get_logger(__name__)

# Create FastMCP app
app = FastMCP("materials-db")

# Health check will be handled by the HTTP server when running with uvicorn

# HTTP client for API calls with increased timeout and retry configuration
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(300.0, connect=30.0, read=300.0, write=30.0),  # Increased for AFLOW queries
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    transport=httpx.AsyncHTTPTransport(retries=3)
)
MP_API_KEY = os.getenv("MP_API_KEY") #"AY0i5TZn1C2OeMa6S7PUFZ0S9Yml0Vqq" # need to set MP_API_KEY environment variable

# Cache for database queries to improve performance
query_cache = {}
CACHE_EXPIRY_HOURS = 24

def get_cache_key(database: str, query: str, params: Dict[str, Any] = None) -> str:
    """Generate a cache key for database queries."""
    cache_data = {
        "database": database,
        "query": query,
        "params": params or {}
    }
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_string.encode()).hexdigest()

def get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached result if it exists and is not expired."""
    if cache_key in query_cache:
        cached_item = query_cache[cache_key]
        expiry_time = datetime.fromisoformat(cached_item['timestamp']) + timedelta(hours=CACHE_EXPIRY_HOURS)
        if datetime.now() < expiry_time:
            return cached_item['data']
        else:
            # Remove expired cache
            del query_cache[cache_key]
    return None

def set_cached_result(cache_key: str, data: Any):
    """Cache the query result."""
    query_cache[cache_key] = {
        'data': data,
        'timestamp': datetime.now().isoformat()
    }

# Conversion functions removed - conversion is now done by services/structure_converter.py

class MaterialsProjectInput(BaseModel):
    """Input schema for the Materials Project tool."""
    formula: str = Field(description="The chemical formula of the material to search for, e.g., 'LiFePO4', 'SiO2', 'Na3Zr2Si2PO12'.")
    num_return: int = Field(description="The number of materials to return. Default is 1.", default=1)

fields_to_request = ["structure",
        "volume",
        "material_id",
        "formula_pretty",
        "symmetry", # 包含晶系、空间群等信息的对象
        "uncorrected_energy_per_atom",
        "energy_per_atom",
        "formation_energy_per_atom",
        "energy_above_hull",
        "is_stable",
        "band_gap",
        "efermi",
        "theoretical",
        "total_magnetization",
        "density",
        "density_atomic",
        # "PeriodicSite", 
    ]

@app.tool
async def materials_project_query_tool(formula: str, num_return: int = 3, return_frontend_format: bool = True) -> Union[str, Dict[str, Any]]:
    """
    Searches the Materials Project database for a given chemical formula to get structure and properties of a specific inorganic material
    :param formula: formula of the material, str type, e.g. Li3Zr2Si2PO12, NaLiTiAl(PO4)3 or NaLiTiAlP3O12
    :param num_return: maximum number of results to return, default 3
    :param return_frontend_format: if True, returns structured data for frontend use, default True (changed from False)
    :return: information of the material, such as its material id, composition, SymmetryData, Lattice, and PeriodicSite
    """
    if not MP_API_KEY:
        return "Error: MP_API_KEY is not set in the environment variables."

    # Check cache first
    cache_key = get_cache_key("MP", formula, {"num_return": num_return})
    cached_result = get_cached_result(cache_key)
    if cached_result:
        logger.info(f"Using cached MP results for {formula}")
        if return_frontend_format:
            return cached_result
        else:
            return cached_result.get('formatted_text', 'Cached result format error')

    try:
        with MPRester(MP_API_KEY) as mpr:
            # Search for materials with the given formula
            docs = mpr.materials.summary.search(
                formula=formula,
                fields=fields_to_request
            )

        if not docs:
            error_msg = f"No materials found for the formula '{formula}' in the Materials Project database."
            if return_frontend_format:
                return {"error": error_msg, "structures": []}
            return error_msg

        # Collect raw structures (no conversion)
        raw_structures = []
        results = []

        for doc in docs[:num_return]:
            # Generate CIF content
            cif_text = "N/A"
            if doc.structure:
                try:
                    cif_writer = CifWriter(doc.structure, symprec=0.1)
                    cif_text = str(cif_writer)
                except Exception as e:
                    cif_text = f"Error generating CIF: {str(e)}"

            # Extract symmetry info as serializable dict
            symmetry_dict = None
            if doc.symmetry:
                symmetry_dict = {
                    'crystal_system': doc.symmetry.crystal_system.value if hasattr(doc.symmetry, 'crystal_system') else 'Unknown',
                    'symbol': doc.symmetry.symbol if hasattr(doc.symmetry, 'symbol') else 'Unknown',
                    'number': doc.symmetry.number if hasattr(doc.symmetry, 'number') else 0,
                    'point_group': doc.symmetry.point_group if hasattr(doc.symmetry, 'point_group') else 'Unknown'
                }

            # Store raw data (no pymatgen objects - only serializable data)
            raw_structure = {
                'material_id': doc.material_id if hasattr(doc, 'material_id') else 'Unknown',
                'formula_pretty': doc.formula_pretty if hasattr(doc, 'formula_pretty') else 'Unknown',
                # Remove non-serializable pymatgen Structure object
                # 'structure': doc.structure if hasattr(doc, 'structure') else None,
                'symmetry': symmetry_dict,  # Use serializable dict instead of pymatgen object
                'volume': doc.volume if hasattr(doc, 'volume') else 0.0,
                'density': doc.density if hasattr(doc, 'density') else 0.0,
                'band_gap': doc.band_gap if hasattr(doc, 'band_gap') else 0.0,
                'energy_above_hull': doc.energy_above_hull if hasattr(doc, 'energy_above_hull') else 0.0,
                'formation_energy_per_atom': doc.formation_energy_per_atom if hasattr(doc, 'formation_energy_per_atom') else 0.0,
                'energy_per_atom': doc.energy_per_atom if hasattr(doc, 'energy_per_atom') else 0.0,
                'uncorrected_energy_per_atom': doc.uncorrected_energy_per_atom if hasattr(doc, 'uncorrected_energy_per_atom') else 0.0,
                'efermi': doc.efermi if hasattr(doc, 'efermi') else 0.0,
                'density_atomic': doc.density_atomic if hasattr(doc, 'density_atomic') else 0.0,
                'total_magnetization': doc.total_magnetization if hasattr(doc, 'total_magnetization') else 0.0,
                'is_stable': doc.is_stable if hasattr(doc, 'is_stable') else False,
                'theoretical': doc.theoretical if hasattr(doc, 'theoretical') else True,
                'cifContent': cif_text  # Unified field name - CIF contains all structure info
            }
            raw_structures.append(raw_structure)
            
            # Generate text format for backward compatibility
            if doc.structure:
                lattice = doc.structure.lattice
                sites = doc.structure.sites
                lattice_params = (
                    f"a={lattice.a:.3f}, b={lattice.b:.3f}, c={lattice.c:.3f}, "
                    f"α={lattice.alpha:.2f}, β={lattice.beta:.2f}, γ={lattice.gamma:.2f}"
                )
                site_summary = f"{len(sites)} sites total. Species: {', '.join(map(str, doc.structure.composition.elements))}"
            
            symmetry_info = "N/A"
            if doc.symmetry:
                symmetry_info = (f"Crystal System: {doc.symmetry.crystal_system.value}, "
                                 f"Space Group: {doc.symmetry.symbol}")
            
            result_str = (
                f"  - Material ID: {doc.material_id}\n"
                f"    Source URL: https://next-gen.materialsproject.org/materials/{doc.material_id}\n"
                f"    Formula: {doc.formula_pretty}\n"
                f"    Theoretical: {doc.theoretical}\n"
                f"    Symmetry: {symmetry_info}\n"
                f"    Structure:\n"
                f"      - Lattice Parameters (Å, °): {lattice_params if doc.structure else 'N/A'}\n"
                f"      - Sites (PeriodicSite): {sites if doc.structure else 'N/A'}\n"
                f"      - volume: {doc.volume:.4f} Å³\n"
                f"    Energy & Stability:\n"
                f"      - Is Stable: {'Yes' if doc.is_stable else 'No'}\n"
                f"      - Energy Above Hull: {doc.energy_above_hull:.4f} eV/atom\n"
                f"      - Formation Energy: {doc.formation_energy_per_atom:.4f} eV/atom\n"
                f"      - Total Energy: {doc.energy_per_atom:.4f} eV/atom\n"
                f"      - Uncorrected Energy: {doc.uncorrected_energy_per_atom:.4f} eV/atom\n"
                f"    Electronic Properties:\n"
                f"      - Band Gap: {doc.band_gap:.4f} eV\n"
                f"      - Fermi Energy (Efermi): {doc.efermi:.4f} eV\n"
                f"    Physical Properties:\n"
                f"      - Density: {doc.density:.4f} g/cm³\n"
                f"      - Atomic Density: {doc.density_atomic:.4f} atoms/Å³\n"
                f"    Magnetic Properties:\n"
                f"      - Total Magnetization: {doc.total_magnetization:.4f} µB\n"
                f"    CIF Structure (for visualization):\n"
                f"```cif\n{cif_text}\n```"
            )
            results.append(result_str)

        formatted_text = f"Found {len(docs)} materials for '{formula}'. Top results:\n" + "\n\n".join(results)

        # Cache the results (raw data, no conversion)
        cache_data = {
            "database": "MP",
            "structures": raw_structures,
            "formatted_text": formatted_text,
            "count": len(raw_structures),
            "query_info": {
                "formula": formula,
                "num_results": len(raw_structures),
                "database": "MP",
                "timestamp": datetime.now().isoformat()
            }
        }
        set_cached_result(cache_key, cache_data)

        # Always return raw data (conversion will be done by services/structure_converter.py)
        if return_frontend_format:
            return cache_data
        else:
            return {
                "formatted_text": formatted_text,
                "database": "MP",
                "structures": raw_structures,
                "query_info": {
                    "formula": formula,
                    "num_results": len(raw_structures),
                    "database": "MP",
                    "timestamp": datetime.now().isoformat()
                }
            }

    except Exception as e:
        error_msg = f"An error occurred while querying the Materials Project API: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "database": "MP", "structures": []}


class OQMDTool(BaseModel):
    composition: str = Field(description="chemical formula of the target material, e.g. Na3Zr2Si2PO12")

@app.tool
async def get_oqmd_phases(composition: str, num_return: int = 3):
    """
    Searches the Open Quantum Materials Database (OQMD) for materials matching the given chemical formula,
    and extracts essential identification, composition, and structural information.

    :param composition: chemical formula of the target material without brackets, e.g. "Na3PS4", NaLiTiAlP3O12, (not NaLiTiAl(PO4)3), str type
    :param num_return: maximum number of results to return, default 5
    :return: list of simplified material records. Each record is a dict containing:
        - "material_id": unique entry ID in OQMD (from 'entry_id')
        - "icsd_id": unique entry ID in ICSD (from 'icsd_id')
        - "name": material name (e.g., "Na3PS4")
        - "composition": standardized composition string (e.g., "Na3 P1 S4")
        - "structure": dict containing:
            * "space_group": space group symbol (e.g., "P-421c")
            * "unit_cell": 3x3 matrix of lattice vectors
            * "sites": list of atomic sites in "Element @ x y z" format
            * "volume": unit cell volume in Å³
            * "stability": hull distance of the compound, e.g. 0, <-0.1

    Use this tool when you need to retrieve crystal structure and basic metadata for inorganic materials from OQMD.
    Returns an empty list if no results or request fails.
    """
    with qr.QMPYRester() as q:
        kwargs = {
            "composition": composition,
            "limit": num_return,
            "verbose": False,               # skip 'Proceed?' confirmation
            #"element_set": "(Fe-Mn),O",      # composition include (Fe OR Mn) AND O
            #"stability": "0",            # hull distance smaller than -0.1 eV
            #"natom": "<10",                  # number of atoms less than 10
            }
        
        extracted = []
        try:
            list_of_data = q.get_oqmd_phases(**kwargs)

            for entry in list_of_data['data']:
                # Generate CIF text from structure data
                cif_text = "N/A"
                try:
                    from pymatgen.core import Structure, Lattice

                    # Get lattice from unit_cell (3x3 matrix)
                    unit_cell = entry.get("unit_cell", [])
                    sites = entry.get("sites", [])

                    if unit_cell and sites:
                        # Create pymatgen Structure
                        lattice = Lattice(unit_cell)
                        species = []
                        coords = []

                        for site in sites:
                            # Site format: "Element @ x y z"
                            parts = site.split('@')
                            if len(parts) == 2:
                                element = parts[0].strip()
                                coord_str = parts[1].strip().split()
                                if len(coord_str) == 3:
                                    species.append(element)
                                    coords.append([float(x) for x in coord_str])

                        if species and coords:
                            structure = Structure(lattice, species, coords)
                            cif_writer = CifWriter(structure, symprec=0.1)
                            cif_text = str(cif_writer)
                except Exception as e:
                    cif_text = f"Error generating CIF: {str(e)}"

                simplified = {
                    "material_id": entry.get("entry_id", "N/A"),
                    "icsd_id": entry.get("icsd_id", "N/A"),
                    "name": entry.get("name", "N/A"),
                    "composition": entry.get("composition", "N/A").strip(),
                    "structure": {
                        "space_group": entry.get("spacegroup", "N/A"),
                        "unit_cell": entry.get("unit_cell", []),
                        "sites": entry.get("sites", []),
                        "volume": entry.get("volume", "N/A"),
                        "stability": entry.get("stability", "N/A")
                    },
                    "source URL": f"https://oqmd.org/materials/entry/{entry.get('entry_id', 'N/A')}",
                    "cifContent": cif_text  # Unified field name
                }
                extracted.append(simplified)

            if extracted:
                # Return raw data (no conversion)
                return {
                    "database": "OQMD",
                    "structures": extracted,
                    "count": len(extracted),
                    "query_info": {
                        "composition": composition,
                        "num_results": len(extracted),
                        "database": "OQMD",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "error": 'No matched material found in OQMD database',
                    "database": "OQMD",
                    "structures": []
                }

        except Exception as e:
            return {
                "error": f"Error: {e}",
                "database": "OQMD",
                "structures": []
            }


class SearchCODByFormulaInput(BaseModel):
    """Input schema for the SearchCODByFormula tool."""
    formula: str = Field(description="chemical formula in Hill notation, with elements separated by spaces, e.g. 'Na3 O12 P Si2 Zr2'")

@app.tool
async def search_cod_by_formula(formula: str, num_return: int = 3):
    """
    Searches the Crystallography Open Database (COD) for a given chemical formula.

    :param formula: chemical formula (e.g., "NaCl", "H2O", "C8H10N4O2"), will be automatically converted to Hill notation
    :param num_return: maximum number of results to return, default 5
    :return: dict containing JSON-formatted search results if the request succeeds; returns None if the request fails
    Use this tool when you need to retrieve crystal structure data from the Crystallography Open Database (COD) based on a given chemical formula.
    
    Note: COD server (www.crystallography.net) may be slow or unreachable due to network issues.
    If this tool fails, consider using MP, OQMD, or AFLOW databases instead.
    """

    # Check cache first
    cache_key = get_cache_key("COD", formula, {"num_return": num_return})
    cached_result = get_cached_result(cache_key)
    if cached_result:
        logger.info(f"Using cached COD results for {formula}")
        return cached_result

    # Convert formula to Hill notation for COD API
    hill_formula = formula_to_hill_notation(formula)

    base_url="https://www.crystallography.net/cod/result"
    params = {
        "formula": hill_formula,  # COD requires Hill notation with spaces
        "format": 'json'     # return data format
    }

    try:
        # send GET request with timeout (reduced to 15s for faster failure)
        logger.info(f"Querying COD for formula: {formula} (Hill notation: {hill_formula})")
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()  # raise exception if response status code is not 200

        # parse response data
        data = response.json()
    
        # parse JSON data
        results = []
        for i, entry in enumerate(data[:num_return]):  # Limit to requested number of results
            url = f"https://www.crystallography.net/cod/{entry.get('file', 'N/A')}.cif"
            
            try:
                logger.info(f"Downloading CIF {i+1}/{min(num_return, len(data))} from COD...")
                response = requests.get(url, timeout=15)  # download cif file through GET methods with timeout

                if response.status_code == 200:
                    cif_content = response.text
                    logger.info(f"✓ CIF downloaded successfully ({len(cif_content)} chars)")
                else:
                    logger.warning(f"CIF download failed with status {response.status_code}")
                    cif_content = None
            except requests.exceptions.Timeout:
                logger.warning(f"CIF download timeout for {url}")
                cif_content = None
            except Exception as e:
                logger.warning(f"CIF download error: {e}")
                cif_content = None

            simplified_entry = {
                "cod_id": entry.get('codid', 'N/A'),
                "cif_file_id": entry.get('file', 'N/A'),
                "cifContent": cif_content,  # Unified field name
                "chemical_formula": entry.get('formula', 'N/A').strip('- '),
                "mineral_name": entry.get('mineral', 'N/A'),
                "space_group": entry.get('sg', 'N/A'),
                "space_group_number": entry.get('sgNumber', 'N/A'),
                "cell_parameters": {
                    "a": entry.get('a', 'N/A'),
                    "b": entry.get('b', 'N/A'),
                    "c": entry.get('c', 'N/A'),
                    "alpha": entry.get('alpha', 'N/A'),
                    "beta": entry.get('beta', 'N/A'),
                    "gamma": entry.get('gamma', 'N/A')
                },
                "cell_volume": entry.get('vol', 'N/A'),
                "cell_measurement_temperature": entry.get('celltemp', 'N/A'),
                "source URL": f"https://www.crystallography.net/cod/{entry.get('codid', 'N/A')}.html",
                "source_doi": entry.get('doi', 'N/A')
            }
            results.append(simplified_entry)

        if results:
            # Return raw data (no conversion)
            return {
                "database": "COD",
                "structures": results,
                "count": len(results),
                "query_info": {
                    "formula": formula,
                    "num_results": len(results),
                    "database": "COD",
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {
                "error": 'No matched material found in COD database',
                "database": "COD",
                "structures": []
            }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"Request failed: {e}",
            "database": "COD",
            "structures": []
        }
    except ValueError as e:
        return {
            "error": f"JSON data parsing failed: {e}",
            "database": "COD", 
            "structures": []
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "database": "COD",
            "structures": []
        }


def formula_to_hill_notation(formula: str) -> str:
    """
    Convert a chemical formula to COD API format (alphabetical order with spaces).

    COD API format rules (NOT standard Hill notation):
    - All elements are listed in alphabetical order
    - Elements are separated by spaces
    - Numbers stay with their elements

    Examples:
        "NaCl" -> "Cl Na"
        "H2O" -> "H2 O"
        "C8H10N4O2" -> "C8 H10 N4 O2"
        "Na3PS4" -> "Na3 P S4"
    
    Note: COD uses alphabetical order, not strict Hill notation.
    """
    import re

    # Parse formula into elements and counts
    # Pattern matches: Element (uppercase + optional lowercase) followed by optional number
    pattern = r'([A-Z][a-z]?)(\d*)'
    matches = re.findall(pattern, formula)

    if not matches:
        return formula

    # Build element dict
    elements = {}
    for element, count in matches:
        if element:  # Skip empty matches
            count_str = count if count else ""
            elements[element] = count_str

    # Sort all elements alphabetically (COD uses pure alphabetical, not Hill notation)
    sorted_elements = []
    for element in sorted(elements.keys()):
        sorted_elements.append(f"{element}{elements[element]}")

    # Join with spaces
    return ' '.join(sorted_elements)


async def process_formula_dict(formula_dict):
    
    def _format_number(x, sig_fig=8):
        if abs(x) < 1e-10:
            return "0"
        magnitude = math.floor(math.log10(abs(x)))
        digits = sig_fig - 1 - magnitude
        if digits < 0:
            digits = 0
        digits = int(digits)
        x_rounded = round(x, digits)
        s = f"{x_rounded:.{digits}f}"
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s

    sorted_elements = sorted(formula_dict.keys())
    total = sum(formula_dict.values())
    stoichiometries = []
    for element in sorted_elements:
        ratio = formula_dict[element] / total
        stoichiometries.append(_format_number(ratio))
    species_str = ','.join(sorted_elements)
    stoichiometry_str = ','.join(stoichiometries)
    return species_str, stoichiometry_str

class AflowSearchInput(BaseModel):
    """Input schema for the SearchCODByFormula tool."""
    formula_dict: dict = Field(description="Dictionary of element symbols and their stoichiometric ratios, e.g., {'Na':3, 'P':1, 'S':4}")

@app.tool
async def get_aflow_data(formula_dict: dict) -> Dict[str, Any]:
    """
    Searches the AFLOW database by specifying element types and stoichiometric ratios.
    Returns simplified material records including ID, composition, and crystal structure.

    :param formula_dict: Dictionary of element symbols and their stoichiometric ratios, e.g., {'Co':1,'N':8,'C':8,'Li':1,'H':24,'O':12}
    :return: Dict containing database results with structures list, each structure containing:
        - "aflow_id": unique AFLOW UID (auid), e.g. "aflow:5db73d703b3b7767"
        - "compound": standardized compound name, e.g. "Na6P2S8"
        - "structure": dict containing:
            * "spacegroup": space group symbol (e.g., "P-42_{1}c")
            * "spacegroup_number": international space group number (e.g., 114)
            * "lattice_parameters": [a, b, c, alpha, beta, gamma] in Å and degrees
            * "volume": unit cell volume in Å³
            * "natoms": total number of atoms in unit cell
            * "positions_fractional": list of atomic positions in fractional coordinates

    Use this tool when you need precise crystal structure data from AFLOW by element & stoichiometry.
    Returns dict with structures list if results found, or error dict if no results or error occurs.
    """

    species, stoichiometry = await process_formula_dict(formula_dict)
    try:
        import time
        import numpy as np
        
        start_time = time.time()
        
        # 使用 aflow Python 库进行搜索
        logger.info(f"Searching AFLOW database for species: {species}")
        
        # 使用 aflow 库搜索（不使用 batch 参数）
        results = search().filter(K.species == species)
        
        # 转换为列表，限制为 3 个结果
        result_list = []
        for i, result in enumerate(results):
            if i >= 3:
                break
            result_list.append(result)
        
        if not result_list:
            logger.warning("AFLOW search returned no results")
            return {
                "error": "No results found in AFLOW",
                "database": "AFLOW",
                "structures": []
            }
        
        logger.info(f"AFLOW search returned {len(result_list)} results")
        
        extracted = []
        count = 0
        max_results = 3
        
        for entry in result_list[:max_results]:
            count += 1
            
            # aflow 库返回的是对象，使用 getattr 获取属性
            # 解析晶格参数
            try:
                geometry = getattr(entry, 'geometry', None)
                if geometry is not None and len(geometry) >= 6:
                    # geometry 是 numpy 数组，转换为列表
                    lattice_params = geometry[:6].tolist() if hasattr(geometry, 'tolist') else list(geometry[:6])
                else:
                    lattice_params = ["N/A"] * 6
            except Exception as e:
                logger.warning(f"Failed to parse geometry: {e}")
                lattice_params = ["N/A"] * 6

            # 获取原子位置信息
            try:
                positions = getattr(entry, 'positions_fractional', None)
                if positions is not None:
                    # positions 是 numpy 数组，转换为列表
                    positions = positions.tolist() if hasattr(positions, 'tolist') else list(positions)
                else:
                    positions = []
            except Exception as e:
                logger.warning(f"Failed to parse positions_fractional: {e}")
                positions = []

            # 获取元素类型信息
            try:
                species_list = getattr(entry, 'species', None)
                if species_list:
                    # species 可能是字符串 "Na,Cl" 或列表
                    if isinstance(species_list, str):
                        species_list = species_list.split(',')
                    elif hasattr(species_list, 'tolist'):
                        species_list = species_list.tolist()
                else:
                    species_list = []
            except Exception as e:
                logger.warning(f"Failed to parse species: {e}")
                species_list = []

            # 获取每个原子的类型
            # 注意：AFLOW 的 composition 字段是数量数组 [1, 1]，不是元素名称
            # 我们需要使用 species 字段来获取元素名称
            composition_list = []  # 不使用 composition 字段

            # 生成 CIF 内容
            cif_text = None
            # 检查是否有有效的晶格参数和原子位置
            has_valid_lattice = (
                lattice_params is not None 
                and len(lattice_params) >= 6 
                and lattice_params[0] != "N/A"
            )
            has_valid_positions = positions is not None and len(positions) > 0
            
            if has_valid_lattice and has_valid_positions:
                try:
                    from pymatgen.core import Structure, Lattice
                    
                    compound = getattr(entry, 'compound', '')
                    natoms = len(positions)
                    
                    logger.info(f"Processing AFLOW entry: {compound}, natoms={natoms}, positions={len(positions)}")
                    logger.info(f"  composition_list: {composition_list}")
                    logger.info(f"  species_list: {species_list}")
                    
                    # 创建晶格
                    lattice = Lattice.from_parameters(
                        a=float(lattice_params[0]),
                        b=float(lattice_params[1]),
                        c=float(lattice_params[2]),
                        alpha=float(lattice_params[3]),
                        beta=float(lattice_params[4]),
                        gamma=float(lattice_params[5])
                    )
                    
                    # AFLOW positions_fractional 格式: [[x1,y1,z1], [x2,y2,z2], ...]
                    # 需要从 species 和 composition 字段获取元素类型
                    species = []
                    coords = []
                    
                    # 方法1：使用 AFLOW 的 species 和 composition 字段
                    # species = ['Cl', 'Na'], composition = [1, 1]
                    # 这意味着有 1 个 Cl 原子和 1 个 Na 原子
                    if species_list:
                        logger.info(f"  Using AFLOW species field: {species_list}")
                        
                        # 获取 composition 数量
                        try:
                            composition_attr = getattr(entry, 'composition', None)
                            if composition_attr is not None:
                                if hasattr(composition_attr, 'tolist'):
                                    composition_counts = composition_attr.tolist()
                                elif isinstance(composition_attr, (list, tuple)):
                                    composition_counts = list(composition_attr)
                                else:
                                    composition_counts = []
                                
                                logger.info(f"  Composition counts: {composition_counts}")
                                
                                # 根据 composition 扩展 species
                                if len(species_list) == len(composition_counts):
                                    element_sequence = []
                                    for elem, count in zip(species_list, composition_counts):
                                        element_sequence.extend([elem] * int(count))
                                    
                                    logger.info(f"  Expanded element_sequence: {element_sequence} (len={len(element_sequence)})")
                                    
                                    if len(element_sequence) == natoms:
                                        for i, pos in enumerate(positions):
                                            if len(pos) >= 3:
                                                species.append(element_sequence[i])
                                                coords.append([float(pos[0]), float(pos[1]), float(pos[2])])
                                    else:
                                        logger.warning(f"  Element sequence length mismatch: {len(element_sequence)} != {natoms}")
                                        # 回退到方法2
                                        species = []
                                        coords = []
                                else:
                                    logger.warning(f"  Species/composition length mismatch: {len(species_list)} != {len(composition_counts)}")
                                    # 回退到方法2
                        except Exception as e:
                            logger.warning(f"  Failed to use species/composition: {e}")
                            # 回退到方法2
                    
                    # 方法2：如果方法1失败，从 compound 解析
                    if not species:
                        logger.info(f"  Parsing compound '{compound}' for species")
                        # 从 compound 解析元素和数量，例如 "Cl1Na1" -> ["Cl", "Na"]
                        import re
                        elements_with_counts = re.findall(r'([A-Z][a-z]?)(\d*)', compound)
                        element_sequence = []
                        for elem, count in elements_with_counts:
                            if elem:
                                count = int(count) if count else 1
                                element_sequence.extend([elem] * count)
                        
                        logger.info(f"  Parsed element_sequence: {element_sequence} (len={len(element_sequence)})")
                        
                        if len(element_sequence) == natoms:
                            for i, pos in enumerate(positions):
                                if len(pos) >= 3:
                                    species.append(element_sequence[i])
                                    coords.append([float(pos[0]), float(pos[1]), float(pos[2])])
                        else:
                            logger.warning(f"  Element sequence length mismatch: {len(element_sequence)} != {natoms}")
                    
                    logger.info(f"  Final species: {species} (len={len(species)})")
                    logger.info(f"  Final coords: {len(coords)} positions")
                    
                    if species and coords and len(species) == len(coords):
                        # 创建结构
                        structure = Structure(lattice, species, coords)
                        
                        logger.info(f"  Created structure with composition: {structure.composition}")
                        logger.info(f"  Structure formula: {structure.composition.formula}")
                        logger.info(f"  Structure reduced formula: {structure.composition.reduced_formula}")
                        
                        # 生成 CIF
                        from pymatgen.io.cif import CifWriter
                        cif_writer = CifWriter(structure, symprec=0.1)
                        cif_text = str(cif_writer)
                        auid = getattr(entry, 'auid', 'unknown')
                        
                        # 验证 CIF 内容是否正确
                        cif_formula = structure.composition.reduced_formula
                        if cif_formula not in cif_text:
                            logger.error(f"  CIF VALIDATION FAILED! Expected {cif_formula} not found in CIF")
                            logger.error(f"  CIF first 500 chars: {cif_text[:500]}")
                            # 不使用错误的 CIF
                            cif_text = None
                        else:
                            logger.info(f"✓ Generated valid CIF for AFLOW entry {auid} ({compound}), formula={cif_formula}")
                    else:
                        logger.warning(f"No valid species/coords for CIF generation (species={len(species)}, coords={len(coords)}, positions={len(positions)})")
                        
                except Exception as e:
                    logger.warning(f"Failed to generate CIF from AFLOW data: {e}")
                    import traceback
                    logger.warning(traceback.format_exc())
                    cif_text = None

            # 解析空间群信息
            spacegroup = "N/A"
            spacegroup_number = "N/A"
            try:
                # 使用 spacegroup_relax 属性
                spacegroup_number = getattr(entry, 'spacegroup_relax', 'N/A')
                # 尝试获取空间群符号（如果有的话）
                spacegroup = f"#{spacegroup_number}" if spacegroup_number != "N/A" else "N/A"
            except Exception as e:
                logger.warning(f"Failed to parse space group: {e}")
            
            structure_info = {
                "spacegroup": spacegroup,
                "spacegroup_number": spacegroup_number,
                "lattice_parameters": {
                    "a": lattice_params[0] if len(lattice_params) > 0 else "N/A",
                    "b": lattice_params[1] if len(lattice_params) > 1 else "N/A",
                    "c": lattice_params[2] if len(lattice_params) > 2 else "N/A",
                    "alpha": lattice_params[3] if len(lattice_params) > 3 else "N/A",
                    "beta": lattice_params[4] if len(lattice_params) > 4 else "N/A",
                    "gamma": lattice_params[5] if len(lattice_params) > 5 else "N/A"
                },
                "volume": float(getattr(entry, 'volume_cell', 0)) if getattr(entry, 'volume_cell', None) else "N/A",
                "natoms": int(getattr(entry, 'natoms', 0)) if getattr(entry, 'natoms', None) else "N/A"
            }

            # Create material record with CIF content
            auid = getattr(entry, 'auid', 'N/A')
            compound = getattr(entry, 'compound', 'N/A')
            
            # Log the final CIF status
            if cif_text:
                logger.info(f"CIF generated successfully for {compound} ({auid}), length={len(cif_text)}")
                # Check if CIF contains the correct compound
                if compound != 'N/A' and compound not in cif_text and 'H2' in cif_text:
                    logger.error(f"CIF MISMATCH! Expected {compound} but CIF contains H2")
                    cif_text = None  # Discard incorrect CIF
            else:
                logger.warning(f"No CIF generated for {compound} ({auid})")
            
            material_record = {
                "aflow_id": auid,
                "compound": compound,
                "material_id": auid,
                "formula_pretty": compound,
                "cifContent": cif_text  # Include generated CIF (or None if failed)
            }
            
            # Add complete structure info
            material_record["structure"] = {
                "spacegroup": structure_info.get("spacegroup", "N/A"),
                "spacegroup_number": structure_info.get("spacegroup_number", "N/A"),
                "lattice_parameters": structure_info.get("lattice_parameters", {}),
                "volume": structure_info.get("volume", "N/A"),
                "natoms": structure_info.get("natoms", "N/A"),
                "positions_fractional": positions if positions else []
            }
            extracted.append(material_record)
            
            # Check timeout (max 60 seconds for AFLOW query)
            elapsed_time = time.time() - start_time
            if elapsed_time > 60:
                logger.warning(f"AFLOW query timeout after {elapsed_time:.1f}s, stopping with {len(extracted)} results")
                break

        # Return raw data (no conversion)
        if extracted:
            return {
                "database": "AFLOW",
                "structures": extracted,
                "count": len(extracted),
                "query_info": {
                    "formula_dict": formula_dict,
                    "num_results": len(extracted),
                    "database": "AFLOW",
                    "timestamp": datetime.now().isoformat()
                }
            }
        else:
            return {
                "error": "No results found in AFLOW",
                "database": "AFLOW",
                "structures": []
            }

    except Exception as e:
        return {
            "error": f"[AFLOW] Error during search: {e}",
            "database": "AFLOW",
            "structures": []
        }

# New enhanced tools for frontend integration

@app.tool
async def batch_database_search(formula: str, databases: List[str] = ["MP", "OQMD", "COD"], num_per_db: int = 3) -> Dict[str, Any]:
    """
    Search multiple databases simultaneously for a given formula and return consolidated frontend-compatible results.
    
    :param formula: Chemical formula to search for
    :param databases: List of databases to search (MP, OQMD, COD, AFLOW)
    :param num_per_db: Number of results to get from each database
    :return: Consolidated results from all databases in frontend format
    """
    all_structures = []
    search_results = {
        "formula": formula,
        "timestamp": datetime.now().isoformat(),
        "databases_searched": databases,
        "total_structures": 0,
        "structures": [],
        "database_results": {},
        "errors": []
    }
    
    # Search each database
    for db in databases:
        try:
            if db == "MP":
                result = await materials_project_query_tool(formula, num_per_db, return_frontend_format=True)
                if isinstance(result, dict) and "structures" in result:
                    structures = result["structures"]
                    search_results["database_results"]["MP"] = {
                        "count": len(structures),
                        "success": True
                    }
                    all_structures.extend(structures)
                else:
                    search_results["errors"].append(f"MP search failed or returned unexpected format")
                    
            elif db == "OQMD":
                oqmd_results = await get_oqmd_phases(formula, num_per_db)
                if isinstance(oqmd_results, dict) and "structures" in oqmd_results:
                    # No conversion - just collect raw structures
                    structures = oqmd_results["structures"]
                    all_structures.extend(structures)

                    search_results["database_results"]["OQMD"] = {
                        "count": len(structures),
                        "success": True
                    }
                else:
                    search_results["errors"].append(f"OQMD search failed or returned no results")

            elif db == "COD":
                # Formula will be automatically converted to Hill notation in search_cod_by_formula
                cod_results = await search_cod_by_formula(formula, num_per_db)
                if isinstance(cod_results, dict) and "structures" in cod_results:
                    # No conversion - just collect raw structures
                    structures = cod_results["structures"]
                    all_structures.extend(structures)

                    search_results["database_results"]["COD"] = {
                        "count": len(structures),
                        "success": True
                    }
                else:
                    search_results["errors"].append(f"COD search failed or returned no results")

            elif db == "AFLOW":
                # AFLOW requires formula dict format - this is a simplified parser
                try:
                    # Very basic formula parsing - would need improvement for complex formulas
                    import re
                    elements = re.findall(r'([A-Z][a-z]?)(\d*)', formula)
                    formula_dict = {}
                    for element, count in elements:
                        formula_dict[element] = int(count) if count else 1

                    aflow_results = await get_aflow_data(formula_dict)
                    if isinstance(aflow_results, dict) and "structures" in aflow_results:
                        # No conversion - just collect raw structures
                        structures = aflow_results["structures"]
                        all_structures.extend(structures)

                        search_results["database_results"]["AFLOW"] = {
                            "count": len(structures),
                            "success": True
                        }
                    else:
                        search_results["errors"].append(f"AFLOW search failed or returned no results")
                except Exception as e:
                    search_results["errors"].append(f"AFLOW search error: {str(e)}")
                    
        except Exception as e:
            search_results["errors"].append(f"Error searching {db}: {str(e)}")
            search_results["database_results"][db] = {
                "count": 0,
                "success": False,
                "error": str(e)
            }
    
    search_results["structures"] = all_structures
    search_results["total_structures"] = len(all_structures)
    
    return search_results

# 已禁用：结构生成功能已移除，避免postprocess.py缺失和序列化错误
# @app.tool
# async def generate_and_compare_structures(composition: str, num_generated: int = 5, compare_with_databases: bool = True) -> Dict[str, Any]:
#     """
#     Generate crystal structures for a composition and optionally compare with database results.
#
#     :param composition: Chemical composition to generate structures for
#     :param num_generated: Number of structures to generate
#     :param compare_with_databases: Whether to also search databases for comparison
#     :return: Generated structures and optional database comparison results
#     """
async def generate_and_compare_structures_disabled(composition: str, num_generated: int = 5, compare_with_databases: bool = True) -> Dict[str, Any]:
    """
    [已禁用] 此功能已被禁用，因为存在技术问题。
    请使用数据库查询工具获取结构。
    """
    return {
        "error": "Structure generation功能已禁用。请使用数据库查询工具（MP、OQMD、COD、AFLOW）获取结构。",
        "composition": composition,
        "timestamp": datetime.now().isoformat(),
        "disabled": True
    }

# 原始代码已注释
"""
# 原始实现代码（已禁用）
async def generate_and_compare_structures_original(composition: str, num_generated: int = 5, compare_with_databases: bool = True) -> Dict[str, Any]:
try:
    # Import the crystal generator
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'simulation', 'crystallm'))

    from generate_crystal import generate_structures_for_composition

    # Progress tracking
    progress_messages = []
    def progress_callback(message: str, progress: float):
        progress_messages.append(f"[{progress:.1%}] {message}")
        logger.info(f"Structure generation: {message} ({progress:.1%})")

    # Generate structures
    generation_result = generate_structures_for_composition(
        composition,
        num_samples=num_generated,
        export_json=True,
        progress_callback=progress_callback
    )

    # Return raw generated structures (no conversion)
    generated_structures = generation_result.get("frontend_structures", [])

    result = {
        "database": "Generated",
        "structures": generated_structures,
        "count": len(generated_structures),
        "query_info": {
            "composition": composition,
            "num_results": len(generated_structures),
            "database": "Generated",
            "generator": "CrystaLLM",
            "timestamp": datetime.now().isoformat()
        },
        "generation_result": generation_result,
        "progress_log": progress_messages,
        "database_comparison": None
    }

    # If requested, also search databases for comparison
    if compare_with_databases and generation_result.get("success", False):
        try:
            db_results = await batch_database_search(composition, ["MP", "OQMD"], num_per_db=3)
            result["database_comparison"] = db_results

            # Add comparison summary
            generated_count = len(generated_structures)
            db_count = db_results.get("total_structures", 0)

            result["comparison_summary"] = {
                "generated_structures": generated_count,
                "database_structures": db_count,
                "total_structures": generated_count + db_count,
                "generation_success": generation_result.get("success", False),
                "databases_searched": db_results.get("databases_searched", [])
            }

        except Exception as e:
            result["database_comparison_error"] = str(e)
            logger.error(f"Database comparison failed: {e}")

    return result

except ImportError as e:
    return {
        "error": f"Structure generation module not available: {str(e)}",
        "composition": composition,
        "timestamp": datetime.now().isoformat()
    }
except Exception as e:
    return {
        "error": f"Structure generation failed: {str(e)}",
        "composition": composition,
        "timestamp": datetime.now().isoformat()
    }
"""

@app.tool
async def get_structure_recommendations(formula: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Get comprehensive structure recommendations by searching all available databases.
    (结构生成功能已禁用)

    :param formula: Chemical formula to get recommendations for
    :param max_results: Maximum total number of structure recommendations
    :return: Comprehensive structure recommendations with metadata
    """
    try:
        # Search all databases first
        db_results = await batch_database_search(formula, ["MP", "OQMD", "COD"], num_per_db=3)
        
        recommendations = {
            "formula": formula,
            "timestamp": datetime.now().isoformat(),
            "database_structures": db_results["structures"],
            "generated_structures": [],
            "total_recommendations": 0,
            "sources": {
                "databases": db_results["database_results"],
                "generation": None
            },
            "recommendation_summary": {}
        }
        
        # 结构生成功能已禁用
        # 只返回数据库查询结果
        recommendations["sources"]["generation"] = {
            "success": False,
            "disabled": True,
            "message": "结构生成功能已禁用，仅返回数据库查询结果"
        }
        
        # Combine all recommendations
        all_structures = recommendations["database_structures"] + recommendations["generated_structures"]
        recommendations["total_recommendations"] = len(all_structures)
        
        # Create summary
        db_sources = {}
        for struct in recommendations["database_structures"]:
            db = struct.get("source", {}).get("database", "Unknown")
            db_sources[db] = db_sources.get(db, 0) + 1
        
        recommendations["recommendation_summary"] = {
            "database_breakdown": db_sources,
            "generated_count": len(recommendations["generated_structures"]),
            "total_database_count": len(recommendations["database_structures"]),
            "coverage": "Comprehensive" if recommendations["total_recommendations"] >= 5 else "Limited"
        }
        
        return recommendations
        
    except Exception as e:
        return {
            "error": f"Failed to get structure recommendations: {str(e)}",
            "formula": formula,
            "timestamp": datetime.now().isoformat()
        }

# Health check endpoint
@app.tool
async def health_check() -> Dict[str, Any]:
    """
    Check the health of the materials database server.
    
    Returns:
        Dict containing server health information
    """
    return {
        "service": "materials-db",
        "status": "healthy",
        "version": "1.0.0",
        "available_tools": [
            "materials_project_query_tool",
            "get_oqmd_phases",
            "search_cod_by_formula",
            "get_aflow_data",
            "batch_database_search",
            "generate_and_compare_structures",
            "get_structure_recommendations"
        ],
        "features": [
            "Multi-database search with caching",
            "Frontend-compatible data format conversion",
            "Crystal structure generation integration",
            "Batch processing capabilities",
            "Comprehensive structure recommendations"
        ],
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
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
    host = "0.0.0.0"  # Always bind to all interfaces
    port = int(os.getenv("DATABASE_MCP_PORT", "50006"))
    external_url = os.getenv("DATABASE_MCP_URL", f"http://0.0.0.0:{port}/sse")
    
    logger.info(f"Starting Database MCP Server in SSE mode on http://{host}:{port}")
    logger.info("Using SSE transport")
    logger.info(f"External URL: {external_url}")
    logger.info(f"Internal Endpoint: http://{host}:{port}/sse")

    # Create HTTP app
    http_app = app.http_app(transport="sse")
    
    # Add health check route using Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    
    async def health_check(request):
        """Health check endpoint for database MCP server"""
        return JSONResponse({
            "status": "healthy",
            "service": "database_mcp",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "mp_api_available": bool(MP_API_KEY)
        })
    
    # Add health route to existing routes
    health_route = Route("/health", health_check, methods=["GET"])
    http_app.router.routes.append(health_route)
    
    # Use SSE transport explicitly
    uvicorn.run(
        http_app,
        host=host,
        port=port,
        log_level="info",
        reload=False,
        timeout_keep_alive=300,
        limit_concurrency=100,
        backlog=2048
    )
