"""
app/integrations/vk_teams.py — VK Teams Bot API client.

Sends internal team notifications only. Never sends to customers.
Failures are logged but never raise — notification failure must not
break the processing pipeline.
"""

import logging
from typing import Optional

import httpx

from app.config.settings import settings
from app.core.schemas import PipelineResult, RequestCategory

logger = logging.getLogger(__name__)

_EMOJI = {
    RequestCategory.SPARE_PART_SELECTION:  "🔧",
    RequestCategory.INVOICE_REQUEST:       "📋",
    RequestCategory.DOCUMENTATION_REQUEST: "📄",
    RequestCategory.OTHER:                 "❓",
}
_CONF = {
    "high":   "🟢",
    "medium": "🟡",
    "low":    "🔴",
}


def _conf_band(score: float | None) -> str:
    if score is None: return "low"
    if score >= 0.8:  return "high"
    if score >= 0.6:  return "medium"
    return "low"


def _build_message(
    result: PipelineResult,
    original_message: str,
    source_channel: Optional[str],
) -> str:
    cat_emoji  = _EMOJI.get(result.category, "❓") if result.category else "⚠️"
    band       = _conf_band(result.confidence)
    conf_emoji = _CONF[band]
    badge      = "🚨 ТРЕБУЕТ ПРОВЕРКИ" if result.escalate_to_human else "✅ Авто-черновик"
    conf_pct   = f"{result.confidence:.0%}" if result.confidence is not None else "—"
    cat_val    = result.category.value if result.category else "error"
    missing    = ", ".join(result.missing_fields) if result.missing_fields else "—"
    channel    = source_channel or "не указан"
    preview    = original_message[:280] + ("…" if len(original_message) > 280 else "")

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"{cat_emoji} *Новая заявка* | {badge}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📌 *ID:* {result.request_id}",
        f"📡 *Канал:* {channel}",
        f"*Категория:* {cat_emoji} `{cat_val}`",
        f"*Уверенность:* {conf_emoji} {conf_pct} ({band})",
        "",
        "*Сообщение клиента:*",
        "```",
        preview,
        "```",
        "",
        f"*Недостающие данные:* {missing}",
    ]

    if result.error:
        lines += ["", f"⚠️ *Ошибка:* {result.error}"]

    if result.draft_reply:
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "📝 *ЧЕРНОВИК ОТВЕТА* (клиенту не отправлен)",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "```",
            result.draft_reply,
            "```",
            "",
            "👆 Проверьте и отправьте вручную через Bitrix",
        ]

    return "\n".join(lines)


class VKTeamsClient:

    def __init__(self):
        self.token    = settings.vk_teams_bot_token
        self.chat_id  = settings.vk_teams_chat_id
        self.api_base = settings.vk_teams_api_base.rstrip("/")

    async def send_notification(
        self,
        result:           PipelineResult,
        original_message: str,
        source_channel:   Optional[str] = None,
    ) -> bool:
        if self.token in ("REPLACE_ME", "", None):
            logger.warning("VK Teams token not configured — skipping notification")
            return False

        text   = _build_message(result, original_message, source_channel)
        url    = f"{self.api_base}/messages/sendText"
        params = {"token": self.token, "chatId": self.chat_id,
                  "text": text, "parseMode": "MarkdownV2"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
            if resp.is_success:
                logger.info("VK Teams notification sent for %s", result.request_id)
                return True
            logger.error("VK Teams %s: %s", resp.status_code, resp.text[:200])
            return False
        except Exception as e:
            logger.error("VK Teams exception for %s: %s", result.request_id, e)
            return False


vk_teams_client = VKTeamsClient()
