"""Mistral LLM provider implementation."""

from pathlib import Path
import yaml
import httpx

from src.config.settings import settings
from src.infrastructure.http_client import get_client
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
        self.api_key = api_key or settings.MISTRAL_API_KEY
        self.model = model or settings.MISTRAL_MODEL
        self._load_prompts()

    def _load_prompts(self):
        """Load prompts from YAML config."""
        prompts_path = settings.BASE_DIR / "config" / "prompts.yaml"
        with open(prompts_path, encoding="utf-8") as f:
            self.prompts = yaml.safe_load(f)["prompts"]

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

        client = get_client()
        response = await client.post(
            MISTRAL_API_URL,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

    async def generate_bilingual_summary(self, text: str, max_length: int = 500) -> dict[str, str]:
        """Generate bilingual summary (EN + RU) for paper abstract in one call.

        Args:
            text: Paper abstract to summarize.
            max_length: Maximum summary length per language.

        Returns:
            Dict with 'en' and 'ru' keys containing summaries.
        
        Raises:
            ValueError: If JSON parsing fails or response format is invalid.
        """
        prompt_template = self.prompts["bilingual_summary"]
        prompt = prompt_template.format(text=text, max_length=max_length)

        # Request JSON mode from Mistral
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }

        # Enforce rate limit
        await MISTRAL_RATE_LIMITER.acquire()

        client = get_client()
        response = await client.post(
            MISTRAL_API_URL,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        
        # Parse JSON response
        import json
        try:
            summary_dict = json.loads(content)
            if "en" not in summary_dict or "ru" not in summary_dict:
                raise ValueError("Missing 'en' or 'ru' keys in response")
            return summary_dict
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}") from e
