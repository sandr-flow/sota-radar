"""Centralized configuration for sota-radar."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Project paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    CONFIG_DIR: Path = BASE_DIR / "config"
    
    # Database
    DB_PATH: Path = DATA_DIR / "sota_radar.db"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    
    # LLM
    MISTRAL_API_KEY: str
    MISTRAL_MODEL: str = "mistral-large-latest"
    LLM_PROVIDER: str = "mistral"
    
    # Pipeline
    PIPELINE_INTERVAL_MINUTES: int = 5
    MAX_RESULTS_PER_CATEGORY: int = 100
    PAPERS_PER_DIGEST: int = 10
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton instance
settings = Settings()
