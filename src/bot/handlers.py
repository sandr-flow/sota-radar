"""Command handlers for sota-radar bot."""

import html
import json
import logging
import yaml
from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from src.config.settings import settings
from src.pipeline.priority_queue import add_to_priority_queue
from src.rag import RAGPipeline
from src.sources.huggingface import HuggingFaceSource
from src.storage import session_scope, PaperRepository, UserRepository
from src.storage.models import PaperModel

router = Router()

# Track summary message IDs per user (in-memory, lost on restart)
# Format: {user_id: message_id}
_summary_messages: dict[int, int] = {}

# Gallery state per chat (in-memory, lost on restart)
# Format: {chat_id: {"source": "hf"|"db", "papers": [paper_dicts], "index": int}}
_galleries: dict[int, dict] = {}

# UI constants for text truncation
TITLE_MAX_LENGTH = 55
BUTTON_MAX_LENGTH = 60
TITLE_DISPLAY_LENGTH = 80

# Load localization strings from YAML
def _load_strings() -> dict[str, dict[str, str]]:
    """Load localization strings from config/strings.yaml."""
    strings_path = settings.BASE_DIR / "config" / "strings.yaml"
    with open(strings_path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("strings", {})

STRINGS = _load_strings()


def get_text(key: str, lang: str) -> str:
    """Get localized string."""
    return STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        ]
    ])


def create_gallery_message(paper: dict, index: int, total: int, lang: str, source: str, summary_preview: str | None = None, paper_id: int | None = None, arxiv_id: str | None = None, url: str | None = None, pdf_url: str | None = None) -> tuple[str, InlineKeyboardMarkup]:
    """Create gallery message for a single paper.

    Args:
        paper: Paper dict with title, upvotes (for HF), arxiv_id/id.
        index: Current paper index (0-based).
        total: Total number of papers.
        lang: User language code.
        source: "hf" or "db".
        summary_preview: Summary text preview (optional).
        paper_id: Database paper ID for deep analysis (optional).
        arxiv_id: arXiv ID for link generation (optional).
        url: Paper URL (optional).
        pdf_url: PDF URL (optional).

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

    # Counter button (non-clickable - empty callback_data)
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


def format_paper_response(
    paper_data: dict,
    lang: str,
    summary_text: str | None = None,
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Format paper response with optional summary.

    Args:
        paper_data: Dict with title, url, pdf_url, and optionally id.
        lang: User language code.
        summary_text: Parsed summary text (already extracted from JSON).

    Returns:
        Tuple of (response_text, keyboard or None).
    """
    title = html.escape(paper_data["title"])

    if summary_text:
        summary = html.escape(summary_text)
        response = (
            f"<b>{title}</b>\n\n"
            f"📝 {summary}\n\n"
            f"{get_text('links', lang)}\n"
            f"• <a href=\"{paper_data['url']}\">arXiv</a>\n"
            f"• <a href=\"{paper_data['pdf_url']}\">PDF</a>"
        )
        # Deep Analysis button (only if paper has id)
        keyboard = None
        if paper_data.get("id"):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text("deep_analysis_btn", lang),
                    callback_data=f"deep:{paper_data['id']}"
                )]
            ])
    else:
        response = (
            f"<b>{title}</b>\n\n"
            f"{get_text('summary_pending', lang)}\n\n"
            f"{get_text('links', lang)}\n"
            f"• <a href=\"{paper_data['url']}\">arXiv</a>\n"
            f"• <a href=\"{paper_data['pdf_url']}\">PDF</a>"
        )
        keyboard = None

    return response, keyboard


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command with language selection."""
    with session_scope() as session:
        user_repo = UserRepository(session)
        lang = user_repo.get_language(message.from_user.id)

    await message.answer(
        get_text("welcome", lang),
        parse_mode="HTML",
        reply_markup=get_language_keyboard(),
    )


@router.message(Command("language"))
async def cmd_language(message: Message):
    """Handle /language command."""
    with session_scope() as session:
        user_repo = UserRepository(session)
        lang = user_repo.get_language(message.from_user.id)

    await message.answer(
        get_text("welcome", lang),
        parse_mode="HTML",
        reply_markup=get_language_keyboard(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def callback_language(callback: CallbackQuery):
    """Handle language selection callback."""
    lang = callback.data.split(":")[1]
    
    with session_scope() as session:
        user_repo = UserRepository(session)
        user_repo.set_language(callback.from_user.id, lang)

    await callback.answer()
    await callback.message.edit_text(
        get_text("lang_set", lang),
        parse_mode="HTML",
    )
    # Send onboarding message
    await callback.message.answer(
        get_text("onboarding", lang),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    from src.config import load_config

    with session_scope() as session:
        user_repo = UserRepository(session)
        lang = user_repo.get_language(message.from_user.id)

    # Load categories dynamically
    config = load_config()
    categories_str = ", ".join(c.id for c in config.categories)
    help_text = get_text("help", lang).format(categories=categories_str)

    await message.answer(
        help_text,
        parse_mode="HTML",
    )


@router.message(Command("digest"))
async def cmd_digest(message: Message):
    """Handle /digest command - show trending papers from HuggingFace as gallery."""
    with session_scope() as session:
        user_repo = UserRepository(session)
        lang = user_repo.get_language(message.from_user.id)

    # Send loading message
    loading_msg = await message.answer(
        get_text("loading_trending", lang),
        parse_mode="HTML",
    )

    # Fetch trending papers from HuggingFace
    hf_source = HuggingFaceSource()
    papers = await hf_source.fetch_filtered_papers(limit=10)

    if not papers:
        await loading_msg.edit_text(get_text("no_trending", lang))
        return

    # Fetch summaries from DB
    arxiv_ids = [p.arxiv_id for p in papers]
    summaries_map = {}

    with session_scope() as session:
        for arxiv_id in arxiv_ids:
            stmt = select(PaperModel).where(
                PaperModel.source == "arxiv",
                PaperModel.source_id.like(f"{arxiv_id}%")
            )
            paper = session.execute(stmt).scalars().first()
            if paper and paper.summary_json:
                try:
                    summaries = json.loads(paper.summary_json)
                    summaries_map[arxiv_id] = {
                        "text": summaries.get(lang, summaries.get("en", "")),
                        "id": paper.id,
                    }
                except json.JSONDecodeError:
                    pass

    # Convert papers to dicts with summaries
    papers_dicts = []
    for p in papers:
        paper_data = {
            "title": p.title,
            "arxiv_id": p.arxiv_id,
            "upvotes": p.upvotes,
        }
        if p.arxiv_id in summaries_map:
            paper_data["summary"] = summaries_map[p.arxiv_id]["text"]
            paper_data["db_id"] = summaries_map[p.arxiv_id]["id"]
        papers_dicts.append(paper_data)

    # Store gallery state
    chat_id = message.chat.id
    _galleries[chat_id] = {
        "source": "hf",
        "papers": papers_dicts,
        "index": 0,
        "message_id": loading_msg.message_id,
    }

    # Show first paper
    summary_preview = papers_dicts[0].get("summary")
    paper_id = papers_dicts[0].get("db_id")
    arxiv_id = papers_dicts[0]["arxiv_id"]
    text, keyboard = create_gallery_message(papers_dicts[0], 0, len(papers_dicts), lang, "hf", summary_preview, paper_id, arxiv_id)

    await loading_msg.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@router.message(Command("latest"))
async def cmd_latest(message: Message):
    """Handle /latest command - show recent papers from DB as gallery."""
    # Extract all data inside session scope to avoid DetachedInstanceError
    papers_data = []
    lang = None

    with session_scope() as session:
        repo = PaperRepository(session)
        user_repo = UserRepository(session)
        lang = user_repo.get_language(message.from_user.id)
        # Get recent papers
        papers = repo.get_recent(limit=10)

        # Extract all needed data while in session
        for p in papers:
            paper_data = {
                "id": p.id,
                "title": p.title,
                "url": p.url,
                "pdf_url": p.pdf_url,
            }
            if p.summary_json:
                try:
                    summaries = json.loads(p.summary_json)
                    paper_data["summary"] = summaries.get(lang, summaries.get("en", ""))
                except json.JSONDecodeError:
                    pass
            papers_data.append(paper_data)

    if not papers_data:
        await message.answer(get_text("no_papers", lang))
        return

    # Store gallery state
    chat_id = message.chat.id
    sent_msg = await message.answer(get_text("loading", lang))

    _galleries[chat_id] = {
        "source": "db",
        "papers": papers_data,
        "index": 0,
        "message_id": sent_msg.message_id,
    }

    # Show first paper
    summary_preview = papers_data[0].get("summary")
    text, keyboard = create_gallery_message(papers_data[0], 0, len(papers_data), lang, "db", summary_preview, papers_data[0]["id"], url=papers_data[0]["url"], pdf_url=papers_data[0]["pdf_url"])

    await sent_msg.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )



@router.callback_query(F.data.startswith("gallery_counter:"))
async def callback_gallery_counter(callback: CallbackQuery):
    """Handle gallery counter button - make it non-clickable."""
    await callback.answer()


@router.callback_query(F.data.startswith("gallery_"))
async def callback_gallery_navigate(callback: CallbackQuery):
    """Handle gallery navigation callbacks."""
    # Parse callback data: gallery_hf:2 or gallery_db:1
    parts = callback.data.split(":")
    source = parts[0].replace("gallery_", "")  # "hf" or "db"
    index = int(parts[1])

    chat_id = callback.message.chat.id

    # Get gallery state
    gallery = _galleries.get(chat_id)
    if not gallery:
        await callback.answer("Gallery expired. Run command again.", show_alert=True)
        return

    # Update index
    gallery["index"] = index
    papers = gallery["papers"]

    # Get user language
    with session_scope() as session:
        user_repo = UserRepository(session)
        lang = user_repo.get_language(callback.from_user.id)

    # Get summary, paper_id, and links from paper dict
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

    # Generate new message
    text, keyboard = create_gallery_message(paper, index, len(papers), lang, source, summary_preview, paper_id, arxiv_id, url, pdf_url)

    await callback.answer()
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@router.callback_query(F.data.startswith("paper:"))
async def callback_paper(callback: CallbackQuery):
    """Handle paper selection callback - show full summary."""
    paper_id = int(callback.data.split(":")[1])
    
    # Extract paper data inside session scope
    paper_data = None
    with session_scope() as session:
        repo = PaperRepository(session)
        user_repo = UserRepository(session)
        lang = user_repo.get_language(callback.from_user.id)
        paper = repo.get_by_id(paper_id)
        
        if paper:
            paper_data = {
                "id": paper.id,
                "title": paper.title,
                "url": paper.url,
                "pdf_url": paper.pdf_url,
                "summary_json": paper.summary_json,
            }

    if not paper_data:
        await callback.answer("Paper not found", show_alert=True)
        return

    await callback.answer()

    # Parse summary JSON and format response
    summary_text = None
    if paper_data["summary_json"]:
        try:
            summaries = json.loads(paper_data["summary_json"])
            summary_text = summaries.get(lang, summaries.get("en", get_text("no_summary", lang)))
        except json.JSONDecodeError:
            summary_text = paper_data["summary_json"]  # Fallback for old plain text
    else:
        # No summary yet - add to priority queue
        add_to_priority_queue(paper_data["id"])

    response, keyboard = format_paper_response(paper_data, lang, summary_text)


    user_id = callback.from_user.id
    
    # Try to edit existing summary message, or send new one
    if user_id in _summary_messages:
        try:
            await callback.bot.edit_message_text(
                response,
                chat_id=callback.message.chat.id,
                message_id=_summary_messages[user_id],
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard,
            )
            return
        except Exception:
            # Message might be deleted or too old, send new one
            pass
    
    # Send new summary message and track its ID
    sent_message = await callback.message.answer(
        response,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=keyboard,
    )
    _summary_messages[user_id] = sent_message.message_id


@router.callback_query(F.data.startswith("hf:"))
async def callback_hf_paper(callback: CallbackQuery):
    """Handle HuggingFace paper selection - show paper info by arXiv ID."""
    arxiv_id = callback.data.split(":")[1]

    # Extract paper data inside session scope to avoid DetachedInstanceError
    paper_data = None
    with session_scope() as session:
        user_repo = UserRepository(session)
        lang = user_repo.get_language(callback.from_user.id)
        
        # Try to find paper in DB by arXiv ID
        stmt = select(PaperModel).where(
            PaperModel.source == "arxiv",
            PaperModel.source_id.like(f"{arxiv_id}%")
        )
        paper = session.execute(stmt).scalars().first()
        
        if paper:
            paper_data = {
                "id": paper.id,
                "title": paper.title,
                "url": paper.url,
                "pdf_url": paper.pdf_url,
                "summary_json": paper.summary_json,
            }

    await callback.answer()

    if paper_data:
        # Paper is in DB - parse summary and format
        summary_text = None
        if paper_data["summary_json"]:
            try:
                summaries = json.loads(paper_data["summary_json"])
                summary_text = summaries.get(lang, summaries.get("en", get_text("no_summary", lang)))
            except json.JSONDecodeError:
                summary_text = paper_data["summary_json"]
        else:
            # No summary yet - add to priority queue
            add_to_priority_queue(paper_data["id"])

        response, keyboard = format_paper_response(paper_data, lang, summary_text)
    else:
        # Paper not in DB, show basic info with links only
        url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        response = (
            f"📄 <b>arXiv:{arxiv_id}</b>\n\n"
            f"{get_text('no_summary', lang)}\n\n"
            f"{get_text('links', lang)}\n"
            f"• <a href=\"{url}\">arXiv</a>\n"
            f"• <a href=\"{pdf_url}\">PDF</a>"
        )
        keyboard = None


    user_id = callback.from_user.id
    
    # Try to edit existing summary message, or send new one
    if user_id in _summary_messages:
        try:
            await callback.bot.edit_message_text(
                response,
                chat_id=callback.message.chat.id,
                message_id=_summary_messages[user_id],
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass
    
    # Send new summary message and track its ID
    sent_message = await callback.message.answer(
        response,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=keyboard,
    )
    _summary_messages[user_id] = sent_message.message_id

@router.callback_query(F.data.startswith("deep:"))
async def callback_deep_analysis(callback: CallbackQuery):
    """Handle Deep Analysis button - run RAG pipeline with 3 short messages."""
    paper_id = int(callback.data.split(":")[1])
    
    # Extract paper data inside session scope
    paper_data = None
    with session_scope() as session:
        user_repo = UserRepository(session)
        repo = PaperRepository(session)
        lang = user_repo.get_language(callback.from_user.id)
        paper = repo.get_by_id(paper_id)
        if paper:
            paper_data = {
                "title": paper.title,
                "url": paper.url,
                "pdf_url": paper.pdf_url,
            }

    if not paper_data:
        await callback.answer("Paper not found", show_alert=True)
        return

    # Send loading message
    await callback.answer(get_text("deep_analysis_loading", lang), show_alert=True)
    
    loading_msg = await callback.message.answer(
        get_text("deep_analysis_loading", lang),
        parse_mode="HTML",
    )

    try:
        rag = RAGPipeline()
        title = html.escape(paper_data["title"][:TITLE_DISPLAY_LENGTH])
        
        # Question headers
        headers = [
            get_text("q1_header", lang),
            get_text("q2_header", lang),
            get_text("q3_header", lang),
        ]
        
        # Get answers for all 3 questions
        answers = await rag.analyze_paper_questions(paper_id)
        
        # Delete loading message
        await loading_msg.delete()
        
        # Send 3 separate messages
        for i, (header, answer) in enumerate(zip(headers, answers)):
            answer_text = answer.get(lang, answer.get("en", "No answer."))
            answer_text = html.escape(answer_text)
            
            msg_content = f"{header}\n\n{answer_text}"
            
            # Add links only to last message
            if i == 2:
                msg_content += (
                    f"\n\n{get_text('links', lang)}\n"
                    f"• <a href=\"{paper_data['url']}\">arXiv</a> "
                    f"• <a href=\"{paper_data['pdf_url']}\">PDF</a>"
                )
            
            await callback.message.answer(
                msg_content,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Deep analysis failed: {e}", exc_info=True)
        await loading_msg.edit_text(
            f"❌ Analysis failed: {str(e)[:200]}",
            parse_mode="HTML",
        )




@router.message(F.text)
async def txt_smart_chat(message: Message):
    """Handle generic text messages using Smart Chat pipeline."""
    # Send typing action
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        rag = RAGPipeline()
        response = await rag.smart_chat(message.text)
        
        # Split long responses if needed (Telegram limit is 4096)
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for part in parts:
                await message.answer(part, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await message.answer(response, parse_mode="Markdown", disable_web_page_preview=True)
            
    except Exception as e:
        # Log error but don't crash
        logging.getLogger(__name__).error(f"Smart chat failed: {e}", exc_info=True)
        await message.answer("🤖...?", parse_mode=None)


def register_handlers(dp: Dispatcher):
    """Register all handlers with dispatcher."""
    dp.include_router(router)

