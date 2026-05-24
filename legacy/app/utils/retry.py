"""
app/utils/retry.py — Reusable retry decorator and helpers.

Centralises retry logic so it isn't duplicated across the LLM client,
VK Teams client, and other integration clients.

Uses tenacity under the hood. Configurable retry policies:
  - Standard: 3 attempts, exponential backoff (1s → 2s → 4s)
  - Aggressive: 5 attempts, longer backoff (useful for LLM rate limits)
  - No-retry: for non-idempotent operations

Usage:
    from app.utils.retry import with_retry

    @with_retry()
    async def my_api_call():
        ...

TODO:
  - Implement with_retry() decorator factory
  - Add before_sleep logging (log each retry attempt)
  - Add on_giveup callback (log final failure with context)
  - Export retry_if_5xx, retry_if_network_error predicates
"""

from tenacity import retry, stop_after_attempt, wait_exponential


def with_retry(attempts: int = 3, min_wait: int = 1, max_wait: int = 8):
    """
    Decorator factory: wraps an async function with retry logic.

    Usage:
        @with_retry(attempts=3)
        async def call_api(): ...
    """
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        reraise=True,
    )
