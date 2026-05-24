"""
app/integrations/telegram.py — Telegram Bot API integration.

Responsibilities:
  INBOUND:
    - Parse Telegram Update objects from webhook payloads
    - Extract message text, chat ID, user info, media (photos for nameplate)
    - Normalise to IncomingRequest

  OUTBOUND (post-MVP, after human approval):
    - Send text replies to customers via Bot API
    - Send formatted messages (MarkdownV2)
    - Send documents / images

Note: Telegram is an external customer channel — outbound messages go
directly to the customer. Extra care required:
  - Never send without explicit human approval
  - Log all outbound messages
  - Handle rate limits (30 msg/sec per bot global, 1 msg/sec per chat)

TODO:
  - Implement parse_update(raw_body: dict) -> IncomingRequest
  - Implement send_message(chat_id, text, parse_mode="MarkdownV2") -> bool
  - Add webhook secret token validation (X-Telegram-Bot-Api-Secret-Token)
"""


def parse_update(raw_body: dict) -> dict:
    """Parse a Telegram Update object into a normalised dict."""
    # TODO: extract message.text, message.chat.id, message.from, message.photo
    raise NotImplementedError
