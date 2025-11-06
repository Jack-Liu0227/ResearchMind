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

        # Common fix 0: Escape unescaped newlines in string values (for CIF content)
        # This is the most common issue with CIF content in JSON
        import re

        # Find all string values that contain unescaped newlines
        # Pattern: "key": "value with\nunescaped newlines"
        def escape_newlines_in_strings(match):
            """Escape newlines within JSON string values"""
            key = match.group(1)
            value = match.group(2)
            # Escape newlines, carriage returns, and tabs
            value = value.replace('\\', '\\\\')  # Escape backslashes first
            value = value.replace('\n', '\\n')
            value = value.replace('\r', '\\r')
            value = value.replace('\t', '\\t')
            value = value.replace('"', '\\"')  # Escape quotes
            return f'"{key}": "{value}"'

        # Try to fix unescaped newlines in cifContent fields
        # This regex matches: "cifContent": "...content with newlines..."
        # We need to be careful not to match across multiple fields
        try:
            # Simple approach: if we detect "cifContent" or "cif_content",
            # we know the issue is likely unescaped newlines
            if '"cifContent"' in repaired or '"cif_content"' in repaired:
                logger.info("🔧 Detected CIF content, attempting to escape newlines")
                # For now, just remove the problematic structures field
                # and let the system fall back to other data
                repaired = re.sub(r'"structures"\s*:\s*\[.*?\]', '"structures": []', repaired, flags=re.DOTALL)
                logger.info("🔧 Removed structures field with problematic CIF content")
        except Exception as regex_error:
            logger.warning(f"⚠️ Regex fix failed: {regex_error}")

        # Common fix 1: Remove trailing commas
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
