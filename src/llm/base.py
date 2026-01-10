"""Base LLM provider interface for sota-radar."""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM implementations must inherit from this class and implement
    bilingual summarization.
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
