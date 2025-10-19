"""
Crystal structure generation using CrystaLLM.

This module provides a simplified interface to generate crystal structures
from chemical compositions using the CrystaLLM model.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
import torch
logger = structlog.get_logger(__name__)

# Get the directory where this file is located
_MODULE_DIR = Path(__file__).parent.absolute()


def _setup_crystallm_path():
    """Add CrystaLLM to Python path."""
    # Use local crystallm module
    crystallm_module_path = _MODULE_DIR / "crystallm"
    if crystallm_module_path.exists() and str(_MODULE_DIR) not in sys.path:
        sys.path.insert(0, str(_MODULE_DIR))
        logger.info("Added local CrystaLLM to Python path", path=str(_MODULE_DIR))
    return _MODULE_DIR


def _get_model_path():
    """Get the path to the CrystaLLM pre-trained model."""
    # Use local pre-trained model
    model_path = _MODULE_DIR / "pre-trained-model" / "crystallm_v1_small"
    if model_path.exists():
        logger.info("Found CrystaLLM model", path=str(model_path))
        return str(model_path)

    # Try small model
    model_path = _MODULE_DIR / "pre-trained-model" / "crystallm_v1_small"
    if model_path.exists():
        logger.info("Found CrystaLLM model", path=str(model_path))
        return str(model_path)

    logger.error("CrystaLLM model not found in", path=str(_MODULE_DIR / "pre-trained-model"))
    return None


def generate_crystal_from_composition(
    composition: str,
    device: str = "cuda",
    num_samples: int = 1,
    top_k: int = 10,
    max_new_tokens: int = 2000
) -> Dict[str, Any]:
    """
    Generate crystal structure from chemical composition using CrystaLLM.
    
    Args:
        composition: Chemical composition (e.g., "Si", "GaN", "Fe2O3")
        device: Computing device ("cpu" or "cuda", default: "cuda")
        num_samples: Number of structures to generate (default: 1)
        top_k: Top-k sampling parameter (default: 10)
        max_new_tokens: Maximum tokens to generate (default: 2000)
    
    Returns:
        Dict containing:
        - success: bool - Whether generation succeeded
        - cif_content: str - Generated CIF file content
        - cif_filename: str - Generated CIF filename
        - composition: str - Input composition
        - generation_id: str - Unique generation ID
        - error: str - Error message if failed
    """
    import uuid
    
    generation_id = str(uuid.uuid4())[:12]
    
    try:
        device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"  # Use CUDA if available and specified
        logger.info("Starting crystal structure generation",
                   composition=composition,
                   device=device,
                   num_samples=num_samples,
                   generation_id=generation_id)
        
        # Step 1: Setup CrystaLLM path
        crystallm_path = _setup_crystallm_path()
        if not crystallm_path.exists():
            return {
                "success": False,
                "error": f"CrystaLLM not found at {crystallm_path}",
                "composition": composition,
                "generation_id": generation_id
            }
        
        # Step 2: Get model path
        model_path = _get_model_path()
        if not model_path:
            return {
                "success": False,
                "error": "CrystaLLM pre-trained model not found",
                "composition": composition,
                "generation_id": generation_id
            }
        
        # Step 3: Import CrystaLLM
        try:
            # Import from local module
            import sys
            if str(_MODULE_DIR) not in sys.path:
                sys.path.insert(0, str(_MODULE_DIR))

            from generate_crystal import CrystalStructureGenerator
            logger.info("Successfully imported CrystaLLM")
        except ImportError as e:
            logger.error("Failed to import CrystaLLM", error=str(e), module_dir=str(_MODULE_DIR))
            return {
                "success": False,
                "error": f"Failed to import CrystaLLM: {str(e)}. Module dir: {_MODULE_DIR}",
                "composition": composition,
                "generation_id": generation_id
            }
        
        # Step 4: Create directories in generated_structures
        # Use persistent generated_structures directory
        generated_structures_dir = _MODULE_DIR / "generated_structures"
        generated_structures_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for this generation
        generation_subdir = generated_structures_dir / f"{composition}_{generation_id}"
        prompt_dir = generation_subdir / "prompts"
        generate_dir = generation_subdir / "generated"
        postprocess_input_dir = generation_subdir / "generated"
        postprocess_output_dir = generation_subdir / "processed"

        prompt_dir.mkdir(parents=True, exist_ok=True)
        generate_dir.mkdir(parents=True, exist_ok=True)
        postprocess_output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Created directories in generated_structures",
                   generation_subdir=str(generation_subdir),
                   generation_id=generation_id)
        
        # Step 5: Setup generation parameters
        bin_dir = _MODULE_DIR / "bin"
        crystal_params = {
            'bin_dir': str(bin_dir),
            'prompt_dir': str(prompt_dir),
            'generate_dir': str(generate_dir),
            'postprocess_input_dir': str(postprocess_input_dir),
            'postprocess_output_dir': str(postprocess_output_dir),
            'out_dir': model_path,
            'num_samples': num_samples,
            'top_k': top_k,
            'max_new_tokens': max_new_tokens,
            'device': device
        }

        logger.info("Generation parameters", params=crystal_params, bin_dir=str(bin_dir))
        
        # Step 6: Generate structures
        logger.info("Initializing CrystalStructureGenerator")
        generator = CrystalStructureGenerator(composition, params=crystal_params)

        logger.info("Running generation pipeline - this may take several minutes...")
        logger.info("Progress: Generating prompt...")
        
        # Use the enhanced run_pipeline with frontend format export
        pipeline_result = generator.run_pipeline(export_json=True, json_output_dir=str(generation_subdir))
        
        # Extract results from the new format
        if pipeline_result.get("success", False):
            raw_structures = pipeline_result.get("raw_dataframe")
            processed_structures = pipeline_result.get("processed_dataframe")
            frontend_structures = pipeline_result.get("frontend_structures", [])
        else:
            raw_structures = None
            processed_structures = None
            frontend_structures = []
            logger.error("Pipeline failed", error=pipeline_result.get("message", "Unknown error"))

        # Check if DataFrames are empty
        n_raw = 0 if raw_structures is None or (hasattr(raw_structures, 'empty') and raw_structures.empty) else len(raw_structures)
        n_processed = 0 if processed_structures is None or (hasattr(processed_structures, 'empty') and processed_structures.empty) else len(processed_structures)

        logger.info("Generation completed",
                   n_raw=n_raw,
                   n_processed=n_processed)
        
        # Step 7: Read the first generated CIF file
        # 优先使用后处理的 CIF 文件（postprocess_output_dir）
        # 后处理的文件通常质量更高，已经过验证和优化
        cif_files = list(postprocess_output_dir.glob("**/*.cif"))
        cif_source = "postprocessed"

        if not cif_files:
            # 如果没有后处理的文件，尝试使用原始生成的文件
            logger.warning("No postprocessed CIF files found, trying raw structures")
            cif_files = list(generate_dir.glob("**/*.cif"))
            cif_source = "raw"

        if not cif_files:
            logger.error("No CIF files generated in either postprocessed or raw directories")
            return {
                "success": False,
                "error": "No CIF files were generated",
                "composition": composition,
                "generation_id": generation_id
            }

        # Read all generated CIF files
        cif_contents = []
        for cif_file in cif_files:
            with open(cif_file, 'r', encoding='utf-8') as f:
                cif_contents.append(f.read())

        logger.info("Successfully read all CIF files",
                   source=cif_source,
                   total_files=len(cif_files))

        # Step 8: Return result (keeping files in generated_structures directory)
        result = {
            "success": True,
            "cif_contents": cif_contents,  # Changed from cif_content to cif_contents
            "cif_filenames": [f.name for f in cif_files],
            "composition": composition,
            "generation_id": generation_id,
            "num_generated": len(cif_files),
            "cif_source": cif_source,  # "postprocessed" or "raw"
            "cif_file_path": str(cif_file),
            "model_used": Path(model_path).name,
            "device": device
        }
        
        # Generate frontend-compatible structures from CIF contents
        frontend_structures = []
        try:
            # Import the function from the same directory
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "generate_crystal", 
                _MODULE_DIR / "generate_crystal.py"
            )
            generate_crystal_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(generate_crystal_module)
            convert_cif_to_frontend_format = generate_crystal_module.convert_cif_to_frontend_format
            
            for i, cif_content in enumerate(cif_contents):
                cif_filename = result["cif_filenames"][i]
                frontend_structure = convert_cif_to_frontend_format(
                    cif_content=cif_content,
                    filename=cif_filename,
                    composition=composition,
                    generation_id=generation_id
                )
                if frontend_structure:
                    frontend_structures.append(frontend_structure)
                    
            logger.info(f"Generated {len(frontend_structures)} frontend structures from {len(cif_contents)} CIF files")
                    
        except Exception as e:
            logger.warning(f"Failed to generate frontend structures: {e}")
            frontend_structures = []
        
        # Add frontend structures to result
        result["frontend_structures"] = frontend_structures
        result["num_frontend_structures"] = len(frontend_structures)
            
        return result
    
    except Exception as e:
        logger.error("Error in crystal structure generation",
                    error=str(e),
                    composition=composition,
                    exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "composition": composition,
            "generation_id": generation_id,
            "frontend_structures": [],
            "num_frontend_structures": 0
        }
