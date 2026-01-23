"""LLM Gateway factory for provider selection."""

from __future__ import annotations

from src.config.settings import settings
from src.llm.base import BaseLLMProvider
from src.llm.mistral import MistralProvider


def get_provider(provider_name: str | None = None, **kwargs) -> BaseLLMProvider:
    """Get LLM provider by name.

    Args:
        provider_name: Provider identifier. Defaults to settings.LLM_PROVIDER.
        **kwargs: Additional arguments for provider initialization (e.g. model).

    Returns:
        Configured LLM provider instance.

    Raises:
        ValueError: If provider is not supported.
    """
    if provider_name is None:
        provider_name = settings.LLM_PROVIDER

    providers = {
        "mistral": MistralProvider,
    }

    if provider_name not in providers:
        supported = ", ".join(providers.keys())
        raise ValueError(f"Unknown provider: {provider_name}. Supported: {supported}")

    return providers[provider_name](**kwargs)
