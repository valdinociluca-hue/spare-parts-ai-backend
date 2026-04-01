"""
app/agents/orchestrator.py — Pipeline coordinator.

MVP pipeline:  ClassifierAgent → PipelineResult
Future pipeline: ClassifierAgent → RAGAgent → ResponderAgent → PipelineResult

Services call orchestrator.run() — never individual agents directly.
This makes it easy to extend the pipeline without touching service code.
"""

import logging

from app.agents.classifier import ClassifierAgent
from app.core.exceptions import LLMAPIError, LLMParseError
from app.core.schemas import IncomingRequest, PipelineResult, RequestStatus

logger = logging.getLogger(__name__)

_classifier = ClassifierAgent()


class Orchestrator:

    async def run(self, request: IncomingRequest, request_id: str) -> PipelineResult:
        """
        Run the full agent pipeline for one incoming request.
        Returns a PipelineResult — never raises. Errors are captured in result.error.
        """
        try:
            result = await _classifier.run(request.message_text)

            return PipelineResult(
                request_id        = request_id,
                category          = result.category,
                confidence        = result.confidence,
                escalate_to_human = result.escalate_to_human,
                draft_reply       = result.draft_reply,
                missing_fields    = result.missing_fields,
                status            = RequestStatus.DRAFT_READY,
            )

        except (LLMAPIError, LLMParseError) as e:
            logger.error("Pipeline LLM failure for %s: %s", request_id, e)
            return PipelineResult(
                request_id        = request_id,
                escalate_to_human = True,
                status            = RequestStatus.ERROR,
                error             = str(e),
            )

        except Exception as e:
            logger.exception("Unexpected pipeline failure for %s: %s", request_id, e)
            return PipelineResult(
                request_id        = request_id,
                escalate_to_human = True,
                status            = RequestStatus.ERROR,
                error             = f"Unexpected error: {e}",
            )


orchestrator = Orchestrator()
