"""
Custom LLM wrapper with JSON repair for tool calls
"""

import json
import re
import logging
from typing import Any, AsyncIterator
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

logger = logging.getLogger(__name__)


def repair_json(json_str: str) -> str:
    """
    Attempt to repair malformed JSON strings
    
    Common issues:
    - Missing commas between fields
    - Trailing commas
    - Unescaped quotes in strings
    - Single quotes instead of double quotes
    """
    if not json_str or json_str == "{}":
        return "{}"
    
    try:
        # First, try to parse as-is
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ Malformed JSON detected at position {e.pos}: {e.msg}")
        logger.debug(f"Original JSON: {json_str[:500]}...")
        
        # Try common fixes
        repaired = json_str
        
        # Fix 1: Replace single quotes with double quotes (but not in strings)
        # This is tricky, so we'll skip it for now
        
        # Fix 2: Remove trailing commas before } or ]
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
        
        # Fix 3: Add missing commas between fields (heuristic)
        # Look for patterns like: "field": value "field2"
        repaired = re.sub(r'(["\d\]\}])\s+("[\w_]+"\s*:)', r'\1, \2', repaired)
        
        # Fix 4: Escape unescaped quotes in string values
        # This is complex and risky, skip for now
        
        # Fix 5: Remove control characters
        repaired = ''.join(char for char in repaired if ord(char) >= 32 or char in '\n\r\t')
        
        try:
            json.loads(repaired)
            logger.info(f"✅ Successfully repaired JSON")
            return repaired
        except json.JSONDecodeError as e2:
            logger.error(f"❌ Failed to repair JSON: {e2.msg}")
            logger.error(f"Attempted repair: {repaired[:500]}...")
            
            # Last resort: try to extract valid JSON objects
            # Look for the first { and last }
            start = repaired.find('{')
            end = repaired.rfind('}')
            if start != -1 and end != -1 and end > start:
                extracted = repaired[start:end+1]
                try:
                    json.loads(extracted)
                    logger.info(f"✅ Extracted valid JSON from malformed string")
                    return extracted
                except:
                    pass
            
            # Give up and return empty object
            logger.error(f"❌ All repair attempts failed, returning empty object")
            return "{}"


class RobustLiteLlm(LiteLlm):
    """
    LiteLLM wrapper with JSON repair for tool calls
    
    This wrapper intercepts tool call responses and repairs malformed JSON
    before it's parsed by the Google ADK.
    """
    
    async def generate_content_async(
        self,
        *args,
        **kwargs
    ) -> AsyncIterator[types.GenerateContentResponse]:
        """
        Override generate_content_async to add JSON repair
        """
        try:
            async for response in super().generate_content_async(*args, **kwargs):
                # Check if response has tool calls
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            content = candidate.content
                            if hasattr(content, 'parts') and content.parts:
                                for part in content.parts:
                                    # Check for function calls
                                    if hasattr(part, 'function_call') and part.function_call:
                                        func_call = part.function_call
                                        if hasattr(func_call, 'args') and func_call.args:
                                            # The args might be a string that needs parsing
                                            # or already parsed dict
                                            if isinstance(func_call.args, str):
                                                logger.debug(f"🔧 Repairing JSON for tool: {func_call.name}")
                                                repaired_json = repair_json(func_call.args)
                                                # Update the args with repaired JSON
                                                func_call.args = repaired_json
                
                yield response
                
        except Exception as e:
            logger.error(f"❌ Error in RobustLiteLlm: {e}", exc_info=True)
            raise
