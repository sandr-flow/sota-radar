"""Configuration loader for sota-radar."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class CategoryConfig:
    """arXiv category configuration.

    Attributes:
        id: Category identifier (e.g., "cs.LG").
        name: Human-readable name.
        description: Brief description.
    """

    id: str
    name: str
    description: str


@dataclass
class Settings:
    """Global parsing settings.

    Attributes:
        max_results_per_category: Max papers to fetch per category.
        papers_per_digest: Papers to show in digest.
    """

    max_results_per_category: int = 100
    papers_per_digest: int = 10


@dataclass
class Config:
    """Application configuration.

    Attributes:
        categories: List of arXiv categories to track.
        settings: Global settings.
    """

    categories: list[CategoryConfig]
    settings: Settings


def load_config(config_path: Path | str | None = None) -> Config:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to config/categories.yaml.

    Returns:
        Parsed Config object.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "categories.yaml"
    else:
        config_path = Path(config_path)

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    categories = [
        CategoryConfig(
            id=cat["id"],
            name=cat["name"],
            description=cat["description"],
        )
        for cat in data.get("categories", [])
    ]

    settings_data = data.get("settings", {})
    settings = Settings(
        max_results_per_category=settings_data.get("max_results_per_category", 100),
        papers_per_digest=settings_data.get("papers_per_digest", 10),
    )

    return Config(categories=categories, settings=settings)
