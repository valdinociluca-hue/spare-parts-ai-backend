"""
app/tools/escalation.py — Escalation tool: creates a ticket and notifies the team.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import ConversationContext
from app.tools.registry import BaseTool, tool_registry

logger = logging.getLogger(__name__)


class EscalateToHumanTool(BaseTool):
    name        = "escalate_to_human"
    description = (
        "Передать обращение менеджеру, когда невозможно уверенно помочь. "
        "Используй, если: не хватает данных после нескольких уточнений, "
        "уверенность в ответе низкая, запрос нестандартный или пользователь явно просит "
        "связаться с человеком."
    )
    parameters = {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Причина передачи: почему бот не может помочь самостоятельно",
            },
        },
        "required": ["reason"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        reason = args.get("reason", "Запрос требует участия специалиста")

        # Mark context as escalated
        context.escalated = True
        context.escalation_reason = reason

        # Fire VK Teams notification (best-effort, never raises)
        await _notify_team(context, reason)

        return {
            "escalated": True,
            "reason":    reason,
            "message":   (
                "Ваш запрос передан менеджеру. Специалист свяжется с вами в ближайшее время. "
                "Если вопрос срочный — позвоните нам напрямую."
            ),
        }


async def _notify_team(context: ConversationContext, reason: str) -> None:
    """Send escalation alert to VK Teams. Silent on failure."""
    try:
        from app.integrations.vk_teams import vk_teams_client
        from app.config.settings import settings

        if not vk_teams_client.is_configured:
            return

        equipment_info = ""
        eq = context.equipment
        if eq.brand or eq.model_code:
            equipment_info = f"\n🔧 Оборудование: {eq.brand or '?'} {eq.model_code or ''}"

        symptoms = ", ".join(context.reported_symptoms[:3]) if context.reported_symptoms else "не указаны"

        text = (
            "🆘 *Новая эскалация с сайта*\n"
            f"Причина: {reason}{equipment_info}\n"
            f"Симптомы: {symptoms}\n"
            f"Ходов в диалоге: {context.turn_count}"
        )
        await vk_teams_client.send_text(text)
    except Exception:
        logger.debug("VK Teams escalation notification failed (non-fatal)")


tool_registry.register(EscalateToHumanTool())
