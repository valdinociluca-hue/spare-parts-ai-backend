"""
app/services/request_service.py — Request lifecycle orchestration.

Owns the full business workflow for one incoming customer request:
  1. Persist raw request immediately (fail-safe — always saved)
  2. Run the agent pipeline
  3. Persist classification result
  4. Notify team via VK Teams
  5. Update status at each step
  6. Log every step to the audit trail

Never raises — all errors are captured and returned in PipelineResult.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import orchestrator
from app.core.schemas import IncomingRequest, PipelineResult, RequestStatus
from app.db.repositories.request_repository import RequestRepository
from app.integrations.vk_teams import vk_teams_client

logger = logging.getLogger(__name__)


class RequestService:

    def __init__(self, db: AsyncSession):
        self.repo = RequestRepository(db)
        self.db   = db

    async def handle_incoming(self, request: IncomingRequest) -> PipelineResult:
        row = None
        try:
            # Step 1 — persist raw request
            row = await self.repo.create(request)
            await self.repo.append_event(row.id, "received", "success", {
                "channel": request.source_channel,
                "external_id": request.external_id,
            })

            # Step 2 — run agent pipeline
            result = await orchestrator.run(request, request_id=str(row.id))

            # Step 3 — persist classification
            await self.repo.save_classification(row.id, result)
            await self.repo.append_event(row.id, "classified", result.status.value, {
                "category":   result.category.value if result.category else None,
                "confidence": result.confidence,
                "escalate":   result.escalate_to_human,
            })

            # Step 4 — notify team
            notified = await vk_teams_client.send_notification(
                result           = result,
                original_message = request.message_text,
                source_channel   = request.source_channel,
            )
            await self.repo.append_event(
                row.id, "vk_teams_notify",
                "success" if notified else "failure",
            )

            # Step 5 — final status
            final_status = (
                RequestStatus.SENT_TO_TEAM if notified else RequestStatus.DRAFT_READY
            )
            await self.repo.update_status(row, final_status)
            result.status = final_status

            await self.db.commit()
            logger.info(
                "Request %s done: %s confidence=%.2f escalate=%s",
                row.id,
                result.category.value if result.category else "error",
                result.confidence or 0,
                result.escalate_to_human,
            )
            return result

        except Exception as e:
            logger.exception("RequestService unhandled error: %s", e)
            if row:
                try:
                    await self.repo.append_event(row.id, "error", "failure", error_message=str(e))
                    await self.repo.update_status(row, RequestStatus.ERROR)
                    await self.db.commit()
                except Exception:
                    await self.db.rollback()
            else:
                await self.db.rollback()

            return PipelineResult(
                request_id        = str(row.id) if row else "unknown",
                escalate_to_human = True,
                status            = RequestStatus.ERROR,
                error             = str(e),
            )
