"""
app/integrations/bitrix.py — Bitrix24 webhook normaliser.

Bitrix sends webhooks as POST with JSON or form-encoded body.
Field names vary by entity type (lead, deal, activity).
This module normalises everything to IncomingRequest.
"""

import logging
from typing import Any

from app.core.schemas import IncomingRequest

logger = logging.getLogger(__name__)


def _extract_text(fields: dict) -> str:
    for key in ("DESCRIPTION", "COMMENTS", "SUBJECT", "NAME", "TITLE"):
        val = fields.get(key, "")
        if isinstance(val, str) and val.strip():
            return val.strip()
    # Fallback: join all non-empty string fields
    parts = [f"{k}: {v}" for k, v in fields.items()
             if isinstance(v, str) and v.strip() and k not in ("ID", "ASSIGNED_BY_ID")]
    return " | ".join(parts) if parts else "(no message content)"


def _extract_email(fields: dict) -> str | None:
    raw = fields.get("EMAIL")
    if isinstance(raw, list) and raw:
        return raw[0].get("VALUE")
    if isinstance(raw, str) and raw:
        return raw
    return None


def _extract_phone(fields: dict) -> str | None:
    raw = fields.get("PHONE")
    if isinstance(raw, list) and raw:
        return raw[0].get("VALUE")
    if isinstance(raw, str) and raw:
        return raw
    return None


def _detect_channel(fields: dict) -> str:
    combined = " ".join(
        str(fields.get(k, "")) for k in ("SOURCE_ID", "PROVIDER_ID", "CONNECTOR")
    ).lower()
    if "telegram" in combined: return "telegram"
    if "email" in combined or "imap" in combined or "mail" in combined: return "email"
    if "max" in combined or "myteam" in combined: return "max_messenger"
    if "whatsapp" in combined: return "whatsapp"
    return "bitrix"


def parse_webhook(raw_body: dict[str, Any]) -> IncomingRequest:
    """
    Parse a raw Bitrix webhook body into a normalised IncomingRequest.

    Handles:
      {"event": "...", "data": {"FIELDS": {...}}}
      {"event": "...", "data": {...}}
    """
    data   = raw_body.get("data", raw_body.get("DATA", {}))
    fields = data.get("FIELDS", data.get("fields", data))

    entity_id = str(
        fields.get("ID") or fields.get("LEAD_ID") or raw_body.get("entity_id") or "0"
    )

    return IncomingRequest(
        source_channel = _detect_channel(fields),
        external_id    = entity_id,
        message_text   = _extract_text(fields),
        contact_name   = fields.get("NAME") or fields.get("FULL_NAME"),
        contact_email  = _extract_email(fields),
        contact_phone  = _extract_phone(fields),
    )
