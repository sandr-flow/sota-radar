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
class CategoriesConfig:
    """Categories configuration loaded from YAML.

    Attributes:
        categories: List of arXiv categories to track.
    """

    categories: list[CategoryConfig]


def load_config(config_path: Path | str | None = None) -> CategoriesConfig:
    """Load categories configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to config/categories.yaml.

    Returns:
        Parsed CategoriesConfig object.
    """
    if config_path is None:
        from src.config.settings import settings
        config_path = settings.CONFIG_DIR / "categories.yaml"
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

    return CategoriesConfig(categories=categories)

