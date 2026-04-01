"""
app/services/notification_service.py — Outbound notification routing.

Currently: internal team only (VK Teams) — draft_only_mode.
Future: customer-facing channels after human approval.
"""


class NotificationService:

    async def notify_team(self, result, original_message: str, source_channel: str) -> bool:
        """Send classification result to internal team chat."""
        from app.integrations.vk_teams import vk_teams_client
        return await vk_teams_client.send_notification(
            result=result,
            original_message=original_message,
            source_channel=source_channel,
        )

    async def notify_customer(self, *args, **kwargs):
        """Post-MVP: send approved reply to customer. Disabled in draft_only_mode."""
        from app.config.settings import settings
        if settings.draft_only_mode:
            raise RuntimeError("notify_customer called in draft_only_mode — blocked")
        raise NotImplementedError
