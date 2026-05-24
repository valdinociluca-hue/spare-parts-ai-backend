"""
app/llm/base.py — Abstract LLM client interface.

All concrete LLM clients (YandexGPT, Ollama) implement this interface.
Agents always type-hint against BaseLLMClient — never against a concrete class.
Swapping providers = change one factory line in client.py.
"""

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float | None = None) -> str:
        """
        Send a list of chat messages and return the assistant's reply as a string.

        Args:
            messages: [{"role": "system"|"user"|"assistant", "text": "..."}]
                      Note: YandexGPT uses "text", not "content".
                      The concrete client handles the field name mapping.
            temperature: override the default temperature if needed.

        Returns:
            Raw text content of the assistant message.

        Raises:
            LLMAPIError:   unrecoverable API failure after retries
            LLMParseError: response structure is unexpected
        """
        ...
