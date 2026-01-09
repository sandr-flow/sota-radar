"""Command handlers for sota-radar bot."""

import json
from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.storage import get_session, init_db, PaperRepository

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command."""
    await message.answer(
        "👋 Welcome to <b>sota-radar</b>!\n\n"
        "I deliver AI/ML paper summaries from arXiv.\n\n"
        "Commands:\n"
        "/digest - Get latest paper summaries\n"
        "/help - Show help",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    await message.answer(
        "📚 <b>sota-radar help</b>\n\n"
        "/digest - Show recent papers with AI summaries\n"
        "/start - Welcome message\n"
        "/help - This message\n\n"
        "Papers are fetched from arXiv categories:\n"
        "cs.LG, cs.CL, cs.CV, cs.AI, cs.NE, cs.IR, stat.ML",
        parse_mode="HTML",
    )


@router.message(Command("digest"))
async def cmd_digest(message: Message):
    """Handle /digest command - show recent papers with summaries."""
    init_db()
    session = get_session()
    repo = PaperRepository(session)

    # Get recent papers with summaries
    papers = repo.get_recent(limit=10)
    session.close()

    if not papers:
        await message.answer("No papers yet. Run the pipeline first!")
        return

    # Format response
    response_parts = ["📰 <b>Latest Papers</b>\n"]

    for i, paper in enumerate(papers, 1):
        title = paper.title[:100] + "..." if len(paper.title) > 100 else paper.title
        summary = paper.summary or "No summary yet"
        
        # Truncate summary for Telegram
        if len(summary) > 300:
            summary = summary[:300] + "..."

        response_parts.append(
            f"\n<b>{i}. {title}</b>\n"
            f"📝 {summary}\n"
            f"🔗 <a href=\"{paper.url}\">arXiv</a> | "
            f"<a href=\"{paper.pdf_url}\">PDF</a>"
        )

    response = "\n".join(response_parts)

    # Telegram has 4096 char limit
    if len(response) > 4000:
        response = response[:4000] + "\n\n... (truncated)"

    await message.answer(response, parse_mode="HTML", disable_web_page_preview=True)


def register_handlers(dp: Dispatcher):
    """Register all handlers with dispatcher."""
    dp.include_router(router)
