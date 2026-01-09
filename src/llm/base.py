"""Base LLM provider interface for sota-radar."""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM implementations must inherit from this class and implement
    the required methods for summarization and translation.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return unique identifier for this provider."""
        pass

    @abstractmethod
    async def summarize(self, text: str, max_length: int = 500) -> str:
        """Generate summary for the given text.

        Args:
            text: Text to summarize (typically paper abstract).
            max_length: Maximum summary length in characters.

        Returns:
            Generated summary.
        """
        pass

    @abstractmethod
    async def translate(self, text: str, target_language: str = "ru") -> str:
        """Translate text to target language.

        Args:
            text: Text to translate.
            target_language: Target language code (default: Russian).

        Returns:
            Translated text.
        """
        pass
