"""Shared utility for parsing JSON from LLM responses."""

import json
import logging
import re
from typing import TypeVar

T = TypeVar('T')
logger = logging.getLogger(__name__)


def parse_json_from_llm_response(
    content: str,
    model_class: type[T],
    is_array: bool = True
) -> list[T]:
    """Parse JSON from LLM response, handling multiple formats.

    Args:
        content: Raw text content from LLM response
        model_class: Pydantic model class to parse JSON objects into
        is_array: Whether to expect a JSON array (default True)

    Returns:
        List of parsed model instances

    Handles three formats:
    1. Direct JSON: [{"key": "value"}]
    2. Markdown fence: ```json\n[...]\n```
    3. Embedded JSON: text before [{"key": "value"}] text after
    """
    # Try parsing directly as JSON
    try:
        data = json.loads(content)
        if is_array:
            return [model_class(**item) for item in data]
        else:
            return [model_class(**data)]
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    match = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, list):
                return [model_class(**item) for item in data]
            else:
                return [model_class(**data)]
        except json.JSONDecodeError:
            pass

    # Try finding JSON array anywhere in content
    if is_array:
        match = re.search(r"\[\s*\{.*?\}\s*\]", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return [model_class(**item) for item in data]
            except json.JSONDecodeError:
                pass

    logger.warning(f"Could not parse JSON from LLM response: {content[:200]}")
    return []
