"""
app/utils/text.py — Text processing utilities.

Small, stateless helper functions for text manipulation used across
multiple modules. These have no business logic dependency.

Functions (TODO: implement):
  truncate(text, max_len, suffix="...")
    — Safely truncate text for previews without cutting mid-word

  strip_email_thread(text)
    — Remove quoted email reply chains (lines starting with ">")
    — Remove common email signature patterns

  detect_language(text) -> str
    — Return ISO 639-1 language code ("ru", "en", etc.)
    — Used to ensure draft replies are in the customer's language

  extract_json_block(text) -> str | None
    — Find and extract a JSON block from LLM output that may contain prose
"""


def truncate(text: str, max_len: int = 300, suffix: str = "…") -> str:
    """Truncate text to max_len characters, appending suffix if cut."""
    # TODO: implement word-boundary-aware truncation
    return text[:max_len] + suffix if len(text) > max_len else text


def detect_language(text: str) -> str:
    """Detect the primary language of a text string."""
    # TODO: use langdetect or a lightweight heuristic (Cyrillic detection)
    raise NotImplementedError
