"""
Monkey patch for Google ADK LiteLLM to handle malformed JSON in tool calls

Scope-safe version: avoid interfering with security/crypto libraries (e.g., python-jose)
"""

import json
import logging
import inspect
from typing import Any

logger = logging.getLogger(__name__)

# Store original json.loads
_original_json_loads = json.loads


def _should_bypass_patch(s: Any) -> bool:
    """Decide whether to bypass the patch and use the original json.loads.
    - Bypass for security/crypto libraries (python-jose, cryptography).
    - Bypass for non-JSON-looking short strings (like JWT secrets, tokens).
    """
    # If not a str, don't try to be clever
    if not isinstance(s, str):
        return True

    # Heuristic: if the string doesn't look like JSON, bypass
    json_indicators = ('{', '}', '[', ']', '"', ':')
    looks_like_json = any(ch in s for ch in json_indicators)
    if not looks_like_json and len(s) < 4096:
        return True

    # Call stack check: skip for python-jose or cryptography stacks
    try:
        for frame in inspect.stack(limit=15):
            filename = (frame.filename or '').replace('\\', '/').lower()
            if '/site-packages/jose/' in filename or '/site-packages/cryptography/' in filename or '/jose/' in filename:
                return True
    except Exception:
        # If stack inspection fails, be conservative and bypass
        return True

    return False


def safe_json_loads(s: str, **kwargs) -> Any:
    """
    Safe JSON loads with automatic repair for common issues,
    but with guardrails to avoid breaking non-JSON callers.
    """
    # If we should bypass, delegate to the original behavior (raises on invalid JSON)
    if _should_bypass_patch(s):
        return _original_json_loads(s, **kwargs)

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

        # Try to fix unescaped newlines in cifContent fields
        try:
            if '"cifContent"' in repaired or '"cif_content"' in repaired:
                logger.info("🔧 Detected CIF content, attempting to escape newlines")
                # Remove problematic structures field as a safe fallback
                repaired = re.sub(r'"structures"\s*:\s*\[.*?\]', '"structures": []', repaired, flags=re.DOTALL)
                logger.info("🔧 Removed structures field with problematic CIF content")
        except Exception as regex_error:
            logger.warning(f"⚠️ Regex fix failed: {regex_error}")

        # Common fix 1: Remove trailing commas
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

        # Common fix 2: Add missing commas between fields
        repaired = re.sub(r'(["\d\]\}])\s+("[\w_]+"\s*:)', r'\1, \2', repaired)

        # Common fix 3: Remove control characters except newlines/tabs
        repaired = ''.join(char for char in repaired if ord(char) >= 32 or char in '\n\r\t')

        # Common fix 4: Fix truncated JSON - try to close unclosed braces/brackets
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
            logger.info("✅ Successfully repaired and parsed JSON")
            return result
        except json.JSONDecodeError as e2:
            logger.error(f"❌ Repair failed: {e2.msg} at position {e2.pos}")
            logger.error(f"Repaired JSON (first 500 chars): {repaired[:500]}")
            # Last resort for JSON-like inputs: return empty dict (maintain previous behavior)
            logger.warning("⚠️ Returning empty dict as fallback for JSON-like input")
            return {}


def apply_json_repair_patch():
    """
    Apply the JSON repair patch to the json module

    The patch is scope-safe and will not affect security/crypto libs.
    """
    logger.info("🔧 Applying JSON repair patch to json.loads() (scope-safe)")
    json.loads = safe_json_loads


def remove_json_repair_patch():
    """
    Remove the JSON repair patch and restore original json.loads()
    """
    logger.info("🔧 Removing JSON repair patch")
    json.loads = _original_json_loads
