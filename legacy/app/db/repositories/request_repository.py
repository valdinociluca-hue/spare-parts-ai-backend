"""
app/db/repositories/request_repository.py — Data access for requests.

Services use this repository — they never write ORM queries directly.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import IncomingRequest, PipelineResult, RequestStatus
from app.db.models import ClassificationLog, ProcessingEvent, RequestLog


class RequestRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request: IncomingRequest) -> RequestLog:
        row = RequestLog(
            external_id    = request.external_id,
            source_channel = request.source_channel,
            raw_message    = request.message_text,
            contact_name   = request.contact_name,
            contact_email  = request.contact_email,
            contact_phone  = request.contact_phone,
            status         = RequestStatus.PENDING,
            received_at    = request.received_at,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def save_classification(self, request_id: uuid.UUID, result: PipelineResult) -> None:
        clf = ClassificationLog(
            request_id        = request_id,
            category          = result.category,
            confidence        = result.confidence,
            escalate_to_human = result.escalate_to_human,
            missing_fields    = result.missing_fields,
            draft_reply       = result.draft_reply,
        )
        self.db.add(clf)
        await self.db.flush()

    async def update_status(self, row: RequestLog, status: RequestStatus) -> None:
        row.status     = status
        row.updated_at = datetime.utcnow()
        await self.db.flush()

    async def append_event(
        self,
        request_id:    uuid.UUID,
        event_type:    str,
        status:        str,
        detail:        dict | None = None,
        error_message: str  | None = None,
    ) -> None:
        self.db.add(ProcessingEvent(
            request_id    = request_id,
            event_type    = event_type,
            status        = status,
            detail        = detail,
            error_message = error_message,
        ))
        await self.db.flush()

    async def get_by_id(self, request_id: str) -> RequestLog | None:
        result = await self.db.execute(
            select(RequestLog).where(RequestLog.id == request_id)
        )
        return result.scalar_one_or_none()
