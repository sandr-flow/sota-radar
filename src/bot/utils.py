"""Utility functions for bot module."""

import yaml

from src.config.settings import settings


def _load_strings() -> dict[str, dict[str, str]]:
    """Load localization strings from config/strings.yaml.

    Returns:
        Dict with language codes as keys and string mappings as values.
    """
    strings_path = settings.BASE_DIR / "config" / "strings.yaml"
    with open(strings_path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("strings", {})


# Global strings cache
STRINGS = _load_strings()


def get_text(key: str, lang: str) -> str:
    """Get localized string by key.

    Args:
        key: String key to look up.
        lang: Language code (en, ru, etc.).

    Returns:
        Localized string or key if not found.
    """
    return STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))


def get_language_keyboard() -> "InlineKeyboardMarkup":
    """Create language selection keyboard.

    Returns:
        InlineKeyboardMarkup with language options.
    """
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        ]
    ])
