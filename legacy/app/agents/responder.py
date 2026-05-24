"""
app/agents/responder.py — Draft reply generation agent.

Responsibility: given a classification result and optionally a RAG
context (retrieved catalogue entries, past tickets), generate a safe,
professional draft reply for the team to review.

Responder is separate from Classifier because:
  - It may use different prompts and temperature settings
  - It may need RAG context that Classifier does not
  - It can be swapped or extended independently (e.g. tone variants)
  - Future: streaming response generation

Safety constraint: the responder must NEVER invent prices, availability,
delivery times, or compatibility. It must explicitly request missing data
rather than guessing.

Implementation notes (TODO):
  - Accepts ClassificationResult + optional RAGContext
  - Builds prompt via app/prompts/responder_prompt.py
  - Calls LLM at low temperature
  - Returns DraftReply (text + metadata)
"""

from app.agents.base import BaseAgent


class ResponderAgent(BaseAgent):
    name = "responder"
    description = "Generates a safe draft reply based on classification and optional RAG context."

    async def run(self, input):
        # TODO: build context-aware prompt, call LLM, validate output
        raise NotImplementedError
