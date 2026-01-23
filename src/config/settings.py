"""Centralized configuration for sota-radar."""

from pathlib import Path
from pydantic import field_validator, model_validator
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
    MISTRAL_API_URL: str = "https://api.mistral.ai/v1/chat/completions"
    LLM_PROVIDER: str = "mistral"

    # HTTP
    HTTP_TIMEOUT: float = 60.0
    
    # Pipeline
    PIPELINE_INTERVAL_MINUTES: int = 5
    PRIORITY_QUEUE_CHECK_INTERVAL: int = 30  # seconds
    MAX_RESULTS_PER_CATEGORY: int = 100
    PAPERS_PER_DIGEST: int = 10
    
    # RAG / Vector Store
    CHROMA_PERSIST_DIR: Path = DATA_DIR / "chroma"
    EMBEDDING_MODEL: str = "all-mpnet-base-v2"
    EMBEDDING_OFFLINE_MODE: bool = True  # Skip huggingface.co checks if model cached
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    
    @field_validator("TELEGRAM_BOT_TOKEN", "MISTRAL_API_KEY")
    @classmethod
    def validate_no_placeholder_tokens(cls, v: str) -> str:
        """Validate API keys are not placeholder values."""
        placeholder_values = {
            "your_token_here",
            "your_bot_token_here",
            "your_mistral_api_key_here",
            "replace_with_actual_token",
            "",
            " ",
        }
        if v.lower().strip() in placeholder_values or len(v) < 10:
            raise ValueError(
                f"API key appears to be a placeholder. Please set a valid value in .env"
            )
        return v

    @field_validator("PIPELINE_INTERVAL_MINUTES")
    @classmethod
    def validate_pipeline_interval(cls, v: int) -> int:
        """Validate pipeline interval is positive."""
        if v <= 0:
            raise ValueError("PIPELINE_INTERVAL_MINUTES must be > 0")
        return v

    @field_validator("PAPERS_PER_DIGEST")
    @classmethod
    def validate_papers_per_digest(cls, v: int) -> int:
        """Validate papers per digest is positive."""
        if v <= 0:
            raise ValueError("PAPERS_PER_DIGEST must be > 0")
        return v
    
    @model_validator(mode="after")
    def validate_chunk_sizes(self) -> "Settings":
        """Validate chunk size is greater than overlap."""
        if self.CHUNK_SIZE <= self.CHUNK_OVERLAP:
            raise ValueError(
                f"CHUNK_SIZE ({self.CHUNK_SIZE}) must be > CHUNK_OVERLAP ({self.CHUNK_OVERLAP})"
            )
        return self
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton instance
settings = Settings()
