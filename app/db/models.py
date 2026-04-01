"""
app/db/models.py — SQLAlchemy ORM models.

Three tables:
  request_logs        — one row per incoming customer request
  classification_logs — LLM output linked to a request
  processing_events   — append-only audit trail (never updated)
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float,
    ForeignKey, JSON, String, Text,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship

from app.core.schemas import RequestCategory, RequestStatus


class Base(DeclarativeBase):
    pass


class RequestLog(Base):
    __tablename__ = "request_logs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id      = Column(String(64),  nullable=False, index=True)
    source_channel   = Column(String(32),  nullable=False)
    raw_message      = Column(Text,        nullable=False)
    contact_name     = Column(String(256), nullable=True)
    contact_email    = Column(String(256), nullable=True)
    contact_phone    = Column(String(64),  nullable=True)
    status           = Column(SAEnum(RequestStatus), nullable=False, default=RequestStatus.PENDING)
    received_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at       = Column(DateTime, nullable=False, default=datetime.utcnow,
                              onupdate=datetime.utcnow)

    classification   = relationship("ClassificationLog", back_populates="request", uselist=False)
    events           = relationship("ProcessingEvent",   back_populates="request",
                                    order_by="ProcessingEvent.created_at")


class ClassificationLog(Base):
    __tablename__ = "classification_logs"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id        = Column(UUID(as_uuid=True), ForeignKey("request_logs.id"),
                               nullable=False, unique=True)
    category          = Column(SAEnum(RequestCategory), nullable=True, index=True)
    confidence        = Column(Float,   nullable=True)
    escalate_to_human = Column(Boolean, nullable=False, default=True, index=True)
    equipment_model   = Column(String(256), nullable=True)
    serial_number     = Column(String(128), nullable=True)
    request_summary   = Column(Text,        nullable=True)
    missing_fields    = Column(JSON,        nullable=True)
    draft_reply       = Column(Text,        nullable=True)
    reasoning         = Column(Text,        nullable=True)
    raw_llm_output    = Column(JSON,        nullable=True)
    llm_latency_ms    = Column(Float,       nullable=True)
    created_at        = Column(DateTime,    nullable=False, default=datetime.utcnow)

    request = relationship("RequestLog", back_populates="classification")


class ProcessingEvent(Base):
    __tablename__ = "processing_events"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id    = Column(UUID(as_uuid=True), ForeignKey("request_logs.id"),
                           nullable=False, index=True)
    event_type    = Column(String(64), nullable=False)
    status        = Column(String(16), nullable=False)   # "success" | "failure"
    detail        = Column(JSON,       nullable=True)
    error_message = Column(Text,       nullable=True)
    created_at    = Column(DateTime,   nullable=False, default=datetime.utcnow)

    request = relationship("RequestLog", back_populates="events")
