"""
app/agents/classifier.py — Request classification agent.

Single responsibility: turn a raw customer message into a validated
ClassificationResult. Does not touch the DB or external APIs.

Safety net (in addition to prompt instructions):
  - confidence < threshold → force escalate_to_human = True
  - spare_part_selection + missing fields → force escalate_to_human = True
  - category OTHER → always escalate
"""

import logging

from app.agents.base import BaseAgent
from app.config.settings import settings
from app.core.exceptions import LLMParseError
from app.core.schemas import RequestCategory
from app.llm.client import llm_client
from app.llm.parser import parse_llm_output
from app.llm.schemas import ClassificationResult
from app.prompts.classification import ClassificationPrompt

logger = logging.getLogger(__name__)

_prompt = ClassificationPrompt()


class ClassifierAgent(BaseAgent):
    name        = "classifier"
    description = "Classifies customer request and extracts key fields."

    async def run(self, message_text: str) -> ClassificationResult:
        messages = _prompt.build(customer_message=message_text)
        raw      = await llm_client.chat(messages)

        result   = parse_llm_output(raw, ClassificationResult)

        # ── Safety enforcement (belt-and-suspenders) ─────────────────────
        if result.confidence < settings.confidence_threshold:
            result.escalate_to_human = True
            logger.info(
                "Escalation forced: confidence %.2f < %.2f",
                result.confidence, settings.confidence_threshold,
            )

        if (
            result.category == RequestCategory.SPARE_PART_SELECTION
            and result.missing_fields
        ):
            result.escalate_to_human = True
            logger.info("Escalation forced: spare_part_selection with missing fields")

        if result.category == RequestCategory.OTHER:
            result.escalate_to_human = True

        return result
