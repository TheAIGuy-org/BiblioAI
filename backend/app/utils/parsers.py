"""
Robust parsers for handling LLM outputs.
Critical utility to handle markdown-wrapped JSON from LLMs.
"""
import json
import re
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)


def parse_llm_json(content: str) -> Dict[Any, Any]:
    """
    Reliably extract JSON from LLM markdown output.
    
    Handles common LLM quirks:
    - Markdown code blocks: ```json ... ```
    - Extra whitespace and newlines
    - Preamble text before JSON
    - Trailing explanations after JSON
    
    Args:
        content: Raw LLM response string
        
    Returns:
        Parsed dictionary
        
    Raises:
        json.JSONDecodeError: If no valid JSON found after cleanup
    """
    original_content = content
    
    try:
        # Step 1: Remove markdown code blocks
        content = re.sub(r'```json\s*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'```\s*', '', content)
        
        # Step 2: Try to extract JSON object/array using regex
        # Look for content between outermost { } or [ ]
        json_match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
        
        if json_match:
            content = json_match.group(1)
        
        # Step 3: Clean up whitespace
        content = content.strip()
        
        # Step 4: Parse JSON
        parsed = json.loads(content)
        
        logger.debug(f"[PARSER] Successfully parsed JSON from LLM output")
        return parsed
        
    except json.JSONDecodeError as e:
        logger.error(f"[PARSER] Failed to parse JSON. Original content: {original_content[:200]}")
        logger.error(f"[PARSER] Cleaned content: {content[:200]}")
        logger.error(f"[PARSER] Error: {str(e)}")
        
        # Last resort: try to find and parse the first complete JSON object
        try:
            # Find all potential JSON objects
            objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            for obj in objects:
                try:
                    parsed = json.loads(obj)
                    logger.warning("[PARSER] Used fallback regex extraction")
                    return parsed
                except:
                    continue
        except:
            pass
        
        # If all else fails, raise the original error
        raise json.JSONDecodeError(
            f"Could not extract valid JSON from LLM response. Content: {original_content[:500]}",
            original_content,
            0
        )


def validate_json_schema(data: dict, required_keys: list) -> bool:
    """
    Validate that parsed JSON contains required keys.
    
    Args:
        data: Parsed JSON dictionary
        required_keys: List of required key names
        
    Returns:
        True if all required keys present, False otherwise
    """
    missing_keys = [key for key in required_keys if key not in data]
    
    if missing_keys:
        logger.warning(f"[PARSER] Missing required keys: {missing_keys}")
        return False
    
    return True