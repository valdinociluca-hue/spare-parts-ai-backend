"""
app/llm/schemas.py — Pydantic schemas for LLM structured outputs.

These are the strict contracts between the LLM and the application.
Every field the LLM must return is defined and validated here.
"""

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import RequestCategory


class ExtractedFields(BaseModel):
    equipment_model: str | None = Field(None, description="HoReCa equipment model")
    serial_number:   str | None = Field(None, description="Equipment serial number")
    request_summary: str        = Field(..., description="One-sentence customer need summary")


class ClassificationResult(BaseModel):
    """Full structured output from the ClassifierAgent."""
    category:          RequestCategory
    confidence:        float = Field(..., ge=0.0, le=1.0)
    escalate_to_human: bool
    extracted_fields:  ExtractedFields
    draft_reply:       str  = Field(..., description="Safe draft, never sent automatically")
    missing_fields:    list[str] = Field(default_factory=list)
    reasoning:         str  = Field(..., description="Brief classification reasoning")

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, v))
