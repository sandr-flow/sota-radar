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
    with session_scope() as session:
        user_repo = UserRepository(session)
        lang = user_repo.get_language(message.from_user.id)

    await message.answer(
        get_text("help", lang),
        parse_mode="HTML",
    )


@router.message(Command("digest"))
async def cmd_digest(message: Message):
    """Handle /digest command - show trending papers from HuggingFace."""
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

    # Build inline keyboard with paper titles
    buttons = []
    for paper in papers:
        title = paper.title[:55] + "..." if len(paper.title) > 55 else paper.title
        # Add upvotes indicator
        upvotes_str = f"🔥{paper.upvotes}" if paper.upvotes > 0 else ""
        display_title = f"{upvotes_str} {title}".strip()
        buttons.append([
            InlineKeyboardButton(
                text=display_title[:60],
                callback_data=f"hf:{paper.arxiv_id}",
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await loading_msg.edit_text(
        get_text("digest_header", lang),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.message(Command("latest"))
async def cmd_latest(message: Message):
    """Handle /latest command - show recent papers from DB."""
    # Extract paper data inside session scope
    papers_data = []
    with session_scope() as session:
        repo = PaperRepository(session)
        user_repo = UserRepository(session)
        lang = user_repo.get_language(message.from_user.id)
        # Get recent papers
        papers = repo.get_recent(limit=10)
        for paper in papers:
            papers_data.append({
                "id": paper.id,
                "title": paper.title,
            })

    if not papers_data:
        await message.answer(get_text("no_papers", lang))
        return

    # Build inline keyboard with paper titles
    buttons = []
    for paper in papers_data:
        title = paper["title"][:60] + "..." if len(paper["title"]) > 60 else paper["title"]
        buttons.append([
            InlineKeyboardButton(
                text=title,
                callback_data=f"paper:{paper['id']}",
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        get_text("latest_header", lang),
        parse_mode="HTML",
        reply_markup=keyboard,
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

    # Parse summary JSON
    if paper_data["summary_json"]:
        try:
            summaries = json.loads(paper_data["summary_json"])
            summary = summaries.get(lang, summaries.get("en", get_text("no_summary", lang)))
        except json.JSONDecodeError:
            summary = paper_data["summary_json"]  # Fallback for old plain text
        
        # Build response
        title = html.escape(paper_data["title"])
        summary = html.escape(summary)  # Escape to ensure plain text display
        
        response = (
            f"<b>{title}</b>\n\n"
            f"📝 {summary}\n\n"
            f"{get_text('links', lang)}\n"
            f"• <a href=\"{paper_data['url']}\">arXiv</a>\n"
            f"• <a href=\"{paper_data['pdf_url']}\">PDF</a>"
        )

        # Create Deep Analysis button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text("deep_analysis_btn", lang),
                callback_data=f"deep:{paper_id}"
            )]
        ])
    else:
        # No summary yet - add to priority queue
        add_to_priority_queue(paper_data["id"])
        
        title = html.escape(paper_data["title"])
        response = (
            f"<b>{title}</b>\n\n"
            f"{get_text('summary_pending', lang)}\n\n"
            f"{get_text('links', lang)}\n"
            f"• <a href=\"{paper_data['url']}\">arXiv</a>\n"
            f"• <a href=\"{paper_data['pdf_url']}\">PDF</a>"
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
    
    # Import here to avoid circular imports
    # (Moved to top level)
    
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
        # Paper is in DB
        if paper_data["summary_json"]:
            # Has summary - show it
            try:
                summaries = json.loads(paper_data["summary_json"])
                summary = summaries.get(lang, summaries.get("en", get_text("no_summary", lang)))
            except json.JSONDecodeError:
                summary = paper_data["summary_json"]
            
            title = html.escape(paper_data["title"])
            summary = html.escape(summary)
            
            response = (
                f"<b>{title}</b>\n\n"
                f"📝 {summary}\n\n"
                f"{get_text('links', lang)}\n"
                f"• <a href=\"{paper_data['url']}\">arXiv</a>\n"
                f"• <a href=\"{paper_data['pdf_url']}\">PDF</a>"
            )

            # Create Deep Analysis button
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text("deep_analysis_btn", lang),
                    callback_data=f"deep:{paper_data['id']}"
                )]
            ])
        else:
            # No summary yet - add to priority queue
            add_to_priority_queue(paper_data["id"])
            
            title = html.escape(paper_data["title"])
            response = (
                f"<b>{title}</b>\n\n"
                f"{get_text('summary_pending', lang)}\n\n"
                f"{get_text('links', lang)}\n"
                f"• <a href=\"{paper_data['url']}\">arXiv</a>\n"
                f"• <a href=\"{paper_data['pdf_url']}\">PDF</a>"
            )
            keyboard = None
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
        title = html.escape(paper_data["title"][:80])
        
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



def register_handlers(dp: Dispatcher):
    """Register all handlers with dispatcher."""
    dp.include_router(router)

