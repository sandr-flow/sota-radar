"""Base LLM provider interface for sota-radar."""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM implementations must inherit from this class and implement
    the required methods.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return unique identifier for this provider."""
        pass

    @abstractmethod
    async def generate_bilingual_summary(self, text: str, max_length: int = 500) -> dict[str, str]:
        """Generate bilingual summary for the given text.

        Args:
            text: Text to summarize (typically paper abstract).
            max_length: Maximum summary length per language in characters.

        Returns:
            Dict with 'en' and 'ru' keys containing summaries.
        """
        pass

    @abstractmethod
    async def generate_json_response(self, prompt: str) -> dict[str, Any]:
        """Generate a JSON-structured response for the given prompt.

        Uses provider's JSON mode if available to ensure valid JSON output.

        Args:
            prompt: The prompt requesting a JSON response.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            ValueError: If JSON parsing fails or response format is invalid.
        """
        return sorted(results, key=lambda x: x["distance"])

    @abstractmethod
    async def generate_text(self, prompt: str) -> str:
        """Generate a text response for the given prompt.

        Args:
            prompt: User prompt.

        Returns:
            Generated text response.
        """
        pass
