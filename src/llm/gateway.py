"""LLM Gateway factory for provider selection."""

import os

from src.llm.base import BaseLLMProvider
from src.llm.mistral import MistralProvider


def get_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """Get LLM provider by name.

    Args:
        provider_name: Provider identifier. Defaults to LLM_PROVIDER env var.

    Returns:
        Configured LLM provider instance.

    Raises:
        ValueError: If provider is not supported.
    """
    if provider_name is None:
        provider_name = os.getenv("LLM_PROVIDER", "mistral")

    providers = {
        "mistral": MistralProvider,
    }

    if provider_name not in providers:
        supported = ", ".join(providers.keys())
        raise ValueError(f"Unknown provider: {provider_name}. Supported: {supported}")

    return providers[provider_name]()
