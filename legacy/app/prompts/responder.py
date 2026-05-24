"""
app/prompts/responder.py — Prompt template for draft reply generation.

Used by ResponderAgent. Receives a ClassificationResult and optional
RAG context (retrieved catalogue entries, past similar tickets).

The responder prompt is separate from the classifier prompt because:
  - It may need to incorporate retrieved documents (RAG context)
  - It requires different tone / style instructions
  - Temperature may differ (slightly higher for natural language)
  - It can evolve independently (e.g. add tone variants, per-channel formatting)

TODO:
  - Fill in system prompt with tone guidelines and hard safety rules
  - Add RAG context injection (retrieved chunks as assistant context)
  - Add per-channel formatting rules (Telegram: no markdown tables, etc.)
  - Add examples of good/bad draft replies
"""

from app.prompts.base import BasePrompt


class ResponderPrompt(BasePrompt):
    system = """
    You are writing a professional customer service reply draft.
    TODO: full responder system prompt goes here.
    """

    def build(self, classification_result, rag_context=None) -> list[dict]:
        # TODO: inject classification data, RAG context, return messages
        return [
            {"role": "system", "content": self.system},
            {"role": "user",   "content": "TODO: build user message"},
        ]
