"""
app/integrations/email_gateway.py — Email integration.

Handles inbound and outbound email via an email gateway service
(e.g. Postmark, SendGrid Inbound Parse, Mailgun Routes).

The gateway POSTs a parsed JSON representation of the email to our
webhook endpoint — we never talk to raw SMTP directly.

Inbound:
  - Parse gateway webhook payload
  - Extract subject, body (plain + HTML), sender, attachments
  - Normalise to IncomingRequest

Outbound (post-MVP):
  - Send draft replies via the gateway API
  - Attach PDFs or documents when needed

TODO:
  - Choose and configure an email gateway provider
  - Implement parse_inbound(raw_body: dict) -> IncomingRequest
  - Implement send_reply(to, subject, body, attachments=[]) -> bool
  - Strip email signatures and quoted reply threads from body text
"""


def parse_inbound(raw_body: dict) -> dict:
    """Parse an inbound email gateway payload into a normalised dict."""
    # TODO: extract text content, strip quoted reply, return normalised dict
    raise NotImplementedError
