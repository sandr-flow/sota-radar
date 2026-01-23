"""Gallery UI for browsing papers with navigation."""

import html
from dataclasses import dataclass, field
from typing import Literal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.utils import get_text


@dataclass
class GalleryState:
    """Gallery state for a chat.

    Attributes:
        source: "hf" for HuggingFace, "db" for database.
        papers: List of paper dicts with title, arxiv_id/url, upvotes, summary, etc.
        index: Current paper index (0-based).
        message_id: Telegram message ID to edit.
    """
    source: Literal["hf", "db"]
    papers: list[dict]
    index: int
    message_id: int


class GalleryManager:
    """Manager for paper galleries with navigation.

    Provides gallery creation and navigation for different sources.
    State is stored in-memory (lost on restart).
    """

    def __init__(self):
        """Initialize gallery manager."""
        # Gallery state per chat: {chat_id: GalleryState}
        self._galleries: dict[int, GalleryState] = {}

    def create_gallery(
        self,
        chat_id: int,
        source: Literal["hf", "db"],
        papers: list[dict],
        index: int,
        message_id: int,
    ) -> None:
        """Create or update gallery state.

        Args:
            chat_id: Telegram chat ID.
            source: "hf" or "db".
            papers: List of paper dicts.
            index: Starting index.
            message_id: Message ID to edit.
        """
        self._galleries[chat_id] = GalleryState(
            source=source,
            papers=papers,
            index=index,
            message_id=message_id,
        )

    def get_gallery(self, chat_id: int) -> GalleryState | None:
        """Get gallery state for chat.

        Args:
            chat_id: Telegram chat ID.

        Returns:
            GalleryState or None if not found.
        """
        return self._galleries.get(chat_id)

    def remove_gallery(self, chat_id: int) -> None:
        """Remove gallery state for chat.

        Args:
            chat_id: Telegram chat ID.
        """
        self._galleries.pop(chat_id, None)

    def create_message(
        self,
        paper: dict,
        index: int,
        total: int,
        lang: str,
        source: Literal["hf", "db"],
        summary_preview: str | None = None,
        paper_id: int | None = None,
        arxiv_id: str | None = None,
        url: str | None = None,
        pdf_url: str | None = None,
    ) -> tuple[str, InlineKeyboardMarkup]:
        """Create gallery message for a single paper.

        Args:
            paper: Paper dict with title, upvotes (for HF).
            index: Current paper index (0-based).
            total: Total number of papers.
            lang: User language code.
            source: "hf" or "db".
            summary_preview: Summary text preview.
            paper_id: Database paper ID for deep analysis.
            arxiv_id: arXiv ID for link generation (HF source).
            url: Paper URL (DB source).
            pdf_url: PDF URL (DB source).

        Returns:
            Tuple of (message_text, reply_markup).
        """
        title = html.escape(paper["title"])

        # Build header with upvotes for HF
        if source == "hf":
            upvotes = paper.get("upvotes", 0)
            upvotes_text = f"🔥 {upvotes} " if upvotes > 0 else ""
            header = f"<b>{upvotes_text}{title}</b>"
        else:
            header = f"<b>{title}</b>"

        # Summary preview or placeholder
        if summary_preview:
            preview = html.escape(summary_preview)
        else:
            preview = f"<i>{get_text('summary_pending', lang)}</i>"

        message = f"{header}\n\n{preview}"

        # Add links if available
        if url and pdf_url:
            message += (
                f"\n\n{get_text('links', lang)}\n"
                f"• <a href=\"{url}\">arXiv</a> "
                f"• <a href=\"{pdf_url}\">PDF</a>"
            )
        elif arxiv_id:
            url = f"https://arxiv.org/abs/{arxiv_id}"
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            message += (
                f"\n\n{get_text('links', lang)}\n"
                f"• <a href=\"{url}\">arXiv</a> "
                f"• <a href=\"{pdf_url}\">PDF</a>"
            )

        # Navigation buttons
        nav_buttons = []
        nav_row = []

        # Previous button
        prev_idx = (index - 1) % total
        nav_row.append(
            InlineKeyboardButton(text="◀", callback_data=f"gallery_{source}:{prev_idx}")
        )

        # Counter button (non-clickable)
        nav_row.append(
            InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data=f"gallery_counter:{index}")
        )

        # Next button
        next_idx = (index + 1) % total
        nav_row.append(
            InlineKeyboardButton(text="▶", callback_data=f"gallery_{source}:{next_idx}")
        )

        nav_buttons.append(nav_row)

        # Deep Analysis button (only if paper_id exists)
        if paper_id:
            nav_buttons.append([
                InlineKeyboardButton(text=get_text("deep_analysis_btn", lang), callback_data=f"deep:{paper_id}")
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=nav_buttons)

        return message, keyboard

    def navigate(
        self,
        chat_id: int,
        index: int,
        lang: str,
    ) -> tuple[str, InlineKeyboardMarkup, GalleryState] | None:
        """Navigate to specific index in gallery.

        Args:
            chat_id: Telegram chat ID.
            index: Target paper index.
            lang: User language code.

        Returns:
            Tuple of (message_text, reply_markup, gallery_state) or None if gallery not found.
        """
        gallery = self.get_gallery(chat_id)
        if not gallery:
            return None

        # Update index
        gallery.index = index
        papers = gallery.papers
        source = gallery.source

        # Get paper data
        paper = papers[index]
        summary_preview = paper.get("summary")

        if source == "hf":
            paper_id = paper.get("db_id")
            arxiv_id = paper["arxiv_id"]
            url, pdf_url = None, None
        else:  # db
            paper_id = paper["id"]
            arxiv_id = None
            url = paper.get("url")
            pdf_url = paper.get("pdf_url")

        # Generate message
        text, keyboard = self.create_message(
            paper, index, len(papers), lang, source,
            summary_preview, paper_id, arxiv_id, url, pdf_url
        )

        return text, keyboard, gallery


# Global gallery manager instance
_gallery_manager = GalleryManager()


def get_gallery_manager() -> GalleryManager:
    """Get global gallery manager instance.

    Returns:
        GalleryManager singleton.
    """
    return _gallery_manager
