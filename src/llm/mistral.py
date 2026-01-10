"""Mistral LLM provider implementation."""

import httpx

from src.llm.base import BaseLLMProvider
from src.llm.rate_limiter import MISTRAL_RATE_LIMITER

# Mistral API configuration
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


class MistralProvider(BaseLLMProvider):
    """Mistral AI provider implementation.

    Uses Mistral API for summarization and translation.
    Rate limited to 1 RPS for free tier compliance.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        """Initialize Mistral provider.

        Args:
            api_key: Mistral API key. Defaults to settings.MISTRAL_API_KEY.
            model: Model to use. Defaults to settings.MISTRAL_MODEL.
        """
        from src.config.settings import settings
        
        self.api_key = api_key or settings.MISTRAL_API_KEY
        self.model = model or settings.MISTRAL_MODEL

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "mistral"

    async def _call_api(self, messages: list[dict[str, str]]) -> str:
        """Make rate-limited API call to Mistral.

        Args:
            messages: Chat messages.

        Returns:
            Model response text.
        """
        # Enforce 1 RPS rate limit
        await MISTRAL_RATE_LIMITER.acquire()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                MISTRAL_API_URL,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]

    async def summarize(self, text: str, max_length: int = 500) -> str:
        """Generate summary for paper abstract.

        Args:
            text: Paper abstract to summarize.
            max_length: Maximum summary length.

        Returns:
            Concise summary.
        """
        prompt = f"""Summarize the following scientific paper abstract in 2-3 sentences.
Focus on: main contribution, method, and key results.
Keep it under {max_length} characters.

Abstract:
{text}

Summary:"""

        messages = [{"role": "user", "content": prompt}]
        return await self._call_api(messages)

    async def translate(self, text: str, target_language: str = "ru") -> str:
        """Translate text to target language.

        Args:
            text: Text to translate (English).
            target_language: Target language code.

        Returns:
            Translated text.
        """
        language_names = {
            "ru": "Russian",
            "es": "Spanish",
            "zh": "Chinese",
            "de": "German",
            "fr": "French",
        }
        target_name = language_names.get(target_language, target_language)

        prompt = f"""Translate the following scientific text to {target_name}.
Preserve technical terminology where appropriate.
Output ONLY the translation, without any preamble, introduction, or explanation.
Do not write "Here is the translation" or similar phrases.

Text:
{text}"""

        messages = [{"role": "user", "content": prompt}]
        return await self._call_api(messages)
