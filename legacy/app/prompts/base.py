"""
app/prompts/base.py — Base class for all prompt templates.

Keeping prompts in a dedicated module (not hardcoded in agents or LLM
calls) provides several benefits:

  - Non-engineers can iterate on prompt wording without touching Python
  - Prompts can be versioned and A/B tested independently of code
  - System prompts and user templates are clearly separated
  - Prompt construction logic (variable injection, JSON schema embedding)
    is in one place

Pattern: each prompt is a class with a `build()` method that accepts
typed arguments and returns a list of message dicts (OpenAI format).

Usage:
    from app.prompts.classification import ClassificationPrompt
    messages = ClassificationPrompt().build(customer_message="...")
    response = await llm_client.chat(messages)
"""


class BasePrompt:
    """Abstract base for all prompt templates."""

    system: str = ""   # Override in subclasses

    def build(self, **kwargs) -> list[dict]:
        """Return a messages array for the LLM API call."""
        raise NotImplementedError
