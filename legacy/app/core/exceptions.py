"""
app/core/exceptions.py — Typed application exception hierarchy.
"""


class AppError(Exception):
    """Base for all application errors."""


class LLMError(AppError):
    """Base for LLM-related errors."""


class LLMAPIError(LLMError):
    """LLM API call failed (network, auth, rate limit, 5xx)."""


class LLMParseError(LLMError):
    """LLM returned output that cannot be parsed or schema-validated."""


class IntegrationError(AppError):
    """External service integration failure."""


class NotFoundError(AppError):
    """Requested resource does not exist."""
