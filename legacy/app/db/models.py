"""
app/db/models.py — SQLAlchemy ORM models for the spare parts consultant platform.

Tables:
  Equipment catalog:  brands, equipment_models, serial_ranges
  Knowledge base:     spare_parts, document_sources, document_chunks
  Diagnostics:        error_codes
  SEO:                seo_content
  Conversations:      conversations, messages, conversation_state
  Escalations:        escalations
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


def _uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Equipment catalog
# ─────────────────────────────────────────────────────────────────────────────

class Brand(Base):
    __tablename__ = "brands"

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name       = Column(String(200), nullable=False)
    slug       = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    models      = relationship("EquipmentModel", back_populates="brand", lazy="select")
    spare_parts = relationship("SparePart",      back_populates="brand", lazy="select")


class EquipmentModel(Base):
    __tablename__ = "equipment_models"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    brand_id    = Column(UUID(as_uuid=False), ForeignKey("brands.id"), nullable=False, index=True)
    model_name  = Column(String(300), nullable=False)
    model_code  = Column(String(100), nullable=False, index=True)
    series      = Column(String(200))
    metadata_   = Column("metadata", JSONB, default=dict)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("brand_id", "model_code", name="uq_model_brand_code"),)

    brand         = relationship("Brand",       back_populates="models")
    serial_ranges = relationship("SerialRange", back_populates="model", lazy="select")


class SerialRange(Base):
    __tablename__ = "serial_ranges"

    id             = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    model_id       = Column(UUID(as_uuid=False), ForeignKey("equipment_models.id"), nullable=False, index=True)
    serial_from    = Column(String(100))
    serial_to      = Column(String(100))
    revision_notes = Column(Text)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    model = relationship("EquipmentModel", back_populates="serial_ranges")


# ─────────────────────────────────────────────────────────────────────────────
# Spare parts
# ─────────────────────────────────────────────────────────────────────────────

class SparePart(Base):
    __tablename__ = "spare_parts"

    sku                   = Column(String(100), primary_key=True)
    name                  = Column(String(500), nullable=False)
    description           = Column(Text)
    brand_id              = Column(UUID(as_uuid=False), ForeignKey("brands.id"), index=True)
    compatible_models     = Column(ARRAY(String), default=list)   # model_code[]
    compatible_serial_ids = Column(ARRAY(String), default=list)   # serial_range UUID[]
    category              = Column(String(100), index=True)       # heating, pump, seal, control…
    price                 = Column(Numeric(12, 2))
    stock_qty             = Column(Integer, default=0)
    embedding             = Column(Vector(768))                   # multilingual-e5
    metadata_             = Column("metadata", JSONB, default=dict)
    created_at            = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    brand = relationship("Brand", back_populates="spare_parts")


# ─────────────────────────────────────────────────────────────────────────────
# Equipment error / fault codes
# ─────────────────────────────────────────────────────────────────────────────

class ErrorCode(Base):
    """
    Maps a brand + model pattern + error code to a likely-cause explanation
    and the spare-part SKUs that typically resolve it.

    model_pattern is a shell-style glob ("SCC*", "Appia*", "*") matched
    case-insensitively against the equipment model code.
    """
    __tablename__ = "error_codes"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    brand         = Column(String(100), nullable=False, index=True)
    model_pattern = Column(String(100))                       # glob: "SCC*", "Appia*"
    error_code    = Column(String(50), nullable=False, index=True)  # "E5", "F3", "Err 10"
    description   = Column(Text)
    likely_parts  = Column(ARRAY(String), default=list)       # spare_parts.sku[]
    severity      = Column(String(20))                        # LOW|MEDIUM|HIGH|CRITICAL
    solution      = Column(Text)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("brand", "model_pattern", "error_code",
                         name="uq_errorcode_brand_pattern_code"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# SEO content (per SKU, RU + EN)
# ─────────────────────────────────────────────────────────────────────────────

class SeoContent(Base):
    __tablename__ = "seo_content"

    sku            = Column(String(100), ForeignKey("spare_parts.sku"), primary_key=True)
    title_ru       = Column(Text)
    meta_ru        = Column(Text)
    description_ru = Column(Text)
    keywords_ru    = Column(ARRAY(String), default=list)
    title_en       = Column(Text)
    meta_en        = Column(Text)
    description_en = Column(Text)
    keywords_en    = Column(ARRAY(String), default=list)
    generated_at   = Column(DateTime, default=datetime.utcnow, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# Documents & diagrams
# ─────────────────────────────────────────────────────────────────────────────

class DocumentSource(Base):
    __tablename__ = "document_sources"

    id          = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    source_type = Column(String(50), nullable=False)   # website, pdf, manual, catalog
    source_url  = Column(Text)
    title       = Column(String(500))
    brand_id    = Column(UUID(as_uuid=False), ForeignKey("brands.id"), index=True)
    model_id    = Column(UUID(as_uuid=False), ForeignKey("equipment_models.id"), index=True)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    chunks = relationship("DocumentChunk", back_populates="source", lazy="select")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    source_id    = Column(UUID(as_uuid=False), ForeignKey("document_sources.id"), nullable=False, index=True)
    content      = Column(Text, nullable=False)
    chunk_index  = Column(Integer, nullable=False)
    page_num     = Column(Integer)
    section_type = Column(String(50))   # diagram, parts_list, troubleshooting, spec
    embedding    = Column(Vector(768))
    metadata_    = Column("metadata", JSONB, default=dict)

    source = relationship("DocumentSource", back_populates="chunks")


# ─────────────────────────────────────────────────────────────────────────────
# Conversations
# ─────────────────────────────────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    channel    = Column(String(50), default="web", nullable=False)
    status     = Column(String(50), default="active", nullable=False)  # active, resolved, escalated
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages   = relationship("Message",           back_populates="conversation",
                              lazy="select", order_by="Message.created_at")
    state      = relationship("ConversationState", back_populates="conversation", uselist=False)
    escalation = relationship("Escalation",        back_populates="conversation", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False, index=True)
    role            = Column(String(20), nullable=False)   # user, assistant, tool
    content         = Column(Text, nullable=False)
    tool_name       = Column(String(100))                  # set when role=tool
    tool_result     = Column(JSONB)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class ConversationState(Base):
    __tablename__ = "conversation_state"

    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), primary_key=True)
    state           = Column(JSONB, nullable=False, default=dict)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="state")


# ─────────────────────────────────────────────────────────────────────────────
# Escalations
# ─────────────────────────────────────────────────────────────────────────────

class Escalation(Base):
    __tablename__ = "escalations"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False, unique=True)
    reason          = Column(Text, nullable=False)
    state_snapshot  = Column(JSONB, default=dict)   # ConversationState at escalation time
    status          = Column(String(50), default="pending")  # pending, assigned, resolved
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="escalation")
