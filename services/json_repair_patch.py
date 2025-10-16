"""
Monkey patch for Google ADK LiteLLM to handle malformed JSON in tool calls
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Store original json.loads
_original_json_loads = json.loads


def safe_json_loads(s: str, **kwargs) -> Any:
    """
    Safe JSON loads with automatic repair for common issues
    """
    try:
        return _original_json_loads(s, **kwargs)
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ JSON decode error at position {e.pos}: {e.msg}")
        logger.debug(f"Problematic JSON (first 500 chars): {s[:500]}")
        
        # Try to repair the JSON
        repaired = s
        
        # Common fix 1: Remove trailing commas
        import re
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
        
        # Common fix 2: Add missing commas between fields
        # Pattern: "value" "field": or } "field": or ] "field":
        repaired = re.sub(r'(["\d\]\}])\s+("[\w_]+"\s*:)', r'\1, \2', repaired)
        
        # Common fix 3: Remove control characters except newlines/tabs
        repaired = ''.join(char for char in repaired if ord(char) >= 32 or char in '\n\r\t')
        
        # Common fix 4: Fix truncated JSON - try to close unclosed braces
        open_braces = repaired.count('{') - repaired.count('}')
        open_brackets = repaired.count('[') - repaired.count(']')
        
        if open_braces > 0:
            logger.warning(f"⚠️ Detected {open_braces} unclosed braces, attempting to close")
            repaired += '}' * open_braces
        
        if open_brackets > 0:
            logger.warning(f"⚠️ Detected {open_brackets} unclosed brackets, attempting to close")
            repaired += ']' * open_brackets
        
        try:
            result = _original_json_loads(repaired, **kwargs)
            logger.info(f"✅ Successfully repaired and parsed JSON")
            return result
        except json.JSONDecodeError as e2:
            logger.error(f"❌ Repair failed: {e2.msg} at position {e2.pos}")
            logger.error(f"Repaired JSON (first 500 chars): {repaired[:500]}")
            
            # Last resort: return empty dict for tool arguments
            logger.warning(f"⚠️ Returning empty dict as fallback")
            return {}


def apply_json_repair_patch():
    """
    Apply the JSON repair patch to the json module
    
    This will affect all json.loads() calls in the application,
    making them more resilient to malformed JSON from LLMs.
    """
    logger.info("🔧 Applying JSON repair patch to json.loads()")
    json.loads = safe_json_loads


def remove_json_repair_patch():
    """
    Remove the JSON repair patch and restore original json.loads()
    """
    logger.info("🔧 Removing JSON repair patch")
    json.loads = _original_json_loads
