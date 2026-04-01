"""
tests/unit/test_llm_parser.py — Unit tests for LLM output parsing.

Tests the extract_json() and validate() functions in app/llm/parser.py.

No real LLM or DB calls — pure logic tests.

Coverage goals:
  - Clean JSON string parses correctly
  - JSON wrapped in ```json ... ``` fences parses correctly
  - Invalid JSON raises LLMParseError
  - Valid JSON that fails schema validation raises LLMParseError
  - Edge cases: empty string, truncated JSON, trailing prose

TODO: implement tests once app/llm/parser.py is implemented.
"""

import pytest

# from app.llm.parser import extract_json, validate, LLMParseError


class TestExtractJson:
    def test_placeholder(self):
        """Placeholder — replace with real tests."""
        pass


class TestValidate:
    def test_placeholder(self):
        """Placeholder — replace with real tests."""
        pass
