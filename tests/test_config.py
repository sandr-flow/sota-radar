"""Tests for configuration settings."""

import os
import pytest
from pathlib import Path
from pydantic import ValidationError

from src.config.settings import Settings


class TestSettingsValidation:
    """Test Settings validation."""

    def test_validate_no_placeholder_tokens_short_key(self):
        """Test that short API keys are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                TELEGRAM_BOT_TOKEN="short",
                MISTRAL_API_KEY="alsoshort"
            )
        assert "placeholder" in str(exc_info.value).lower()

    def test_validate_no_placeholder_tokens_empty(self):
        """Test that empty API keys are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                TELEGRAM_BOT_TOKEN="",
                MISTRAL_API_KEY=""
            )
        assert "placeholder" in str(exc_info.value).lower()

    def test_validate_no_placeholder_tokens_placeholder_value(self):
        """Test that placeholder values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                TELEGRAM_BOT_TOKEN="your_token_here",
                MISTRAL_API_KEY="your_mistral_api_key_here"
            )
        assert "placeholder" in str(exc_info.value).lower()

    def test_validate_pipeline_interval_positive(self):
        """Test that pipeline interval must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                TELEGRAM_BOT_TOKEN="valid_token_123456789",
                MISTRAL_API_KEY="valid_key_123456789",
                PIPELINE_INTERVAL_MINUTES=0
            )
        assert "PIPELINE_INTERVAL_MINUTES must be > 0" in str(exc_info.value)

    def test_validate_papers_per_digest_positive(self):
        """Test that papers per digest must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                TELEGRAM_BOT_TOKEN="valid_token_123456789",
                MISTRAL_API_KEY="valid_key_123456789",
                PAPERS_PER_DIGEST=0
            )
        assert "PAPERS_PER_DIGEST must be > 0" in str(exc_info.value)

    def test_validate_chunk_sizes_overlap_greater_than_chunk(self):
        """Test that chunk overlap must be less than chunk size."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                TELEGRAM_BOT_TOKEN="valid_token_123456789",
                MISTRAL_API_KEY="valid_key_123456789",
                CHUNK_SIZE=100,
                CHUNK_OVERLAP=150
            )
        assert "CHUNK_SIZE" in str(exc_info.value)
        assert "CHUNK_OVERLAP" in str(exc_info.value)

    def test_valid_settings(self):
        """Test that valid settings are accepted."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="valid_token_123456789",
            MISTRAL_API_KEY="valid_key_123456789"
        )
        assert settings.TELEGRAM_BOT_TOKEN == "valid_token_123456789"
        assert settings.MISTRAL_API_KEY == "valid_key_123456789"
        assert settings.CHUNK_SIZE == 512  # default value
        assert settings.CHUNK_OVERLAP == 64  # default value

    def test_default_paths(self):
        """Test that default paths are set correctly."""
        settings = Settings(
            TELEGRAM_BOT_TOKEN="valid_token_123456789",
            MISTRAL_API_KEY="valid_key_123456789"
        )
        assert isinstance(settings.BASE_DIR, Path)
        assert isinstance(settings.DATA_DIR, Path)
        assert isinstance(settings.CONFIG_DIR, Path)
        assert settings.DATA_DIR == settings.BASE_DIR / "data"
        assert settings.CONFIG_DIR == settings.BASE_DIR / "config"
