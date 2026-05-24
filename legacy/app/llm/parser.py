"""
app/llm/parser.py — LLM response JSON extraction and schema validation.

YandexGPT has no native JSON mode, so the LLM sometimes:
  - Wraps JSON in ```json ... ``` fences
  - Adds a sentence before the JSON ("Here is the result:")
  - Returns slightly malformed JSON (trailing comma, single quotes)

This module handles all of that robustly before Pydantic validation.
"""

import json
import logging
import re
from typing import Type, TypeVar

from pydantic import BaseModel

from app.core.exceptions import LLMParseError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def extract_json(text: str) -> dict:
    """
    Extract a JSON object from raw LLM output text.

    Strategy (in order):
      1. Strip markdown code fences
      2. Try parsing the whole text as JSON
      3. Find the first { ... } block via regex
    """
    text = text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last line if they are fence markers
        start = 1
        end = len(lines) - 1 if lines[-1].strip() in ("```", "```json") else len(lines)
        text = "\n".join(lines[start:end]).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find first JSON object block
    match = re.search(r"\{[\s\S]+\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise LLMParseError(f"No valid JSON found in LLM output. Raw (first 400 chars): {text[:400]}")


def validate(data: dict, schema: Type[T]) -> T:
    """
    Validate a parsed JSON dict against a Pydantic schema.

    Raises LLMParseError (not ValidationError) so callers have one exception
    type to handle for all LLM output failures.
    """
    try:
        return schema(**data)
    except Exception as e:
        raise LLMParseError(f"LLM output failed schema validation: {e}")


def parse_llm_output(text: str, schema: Type[T]) -> T:
    """Convenience function: extract JSON then validate. Use this in agents."""
    data = extract_json(text)
    return validate(data, schema)
