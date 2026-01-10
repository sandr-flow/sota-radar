"""Command handlers for sota-radar bot."""

import html
import json
from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.storage import get_session, init_db, PaperRepository, UserRepository

router = Router()

# Track summary message IDs per user (in-memory, lost on restart)
# Format: {user_id: message_id}
_summary_messages: dict[int, int] = {}

# Localization strings
STRINGS = {
    "en": {
        "welcome": "👋 Welcome to <b>sota-radar</b>!\n\nI deliver AI/ML paper summaries from arXiv.\n\nSelect your language:",
        "lang_set": "✅ Language set to English",
        "onboarding": "🤖 <b>How to use sota-radar:</b>\n\n📰 /digest — Browse latest AI/ML papers\n   Tap any paper to see its summary\n\n🌐 /language — Change language\n\n📚 /help — Full command list\n\n<i>Papers are updated every 5 minutes from arXiv.</i>",
        "help": "📚 <b>sota-radar help</b>\n\n/digest - Show recent papers with AI summaries\n/language - Change language\n/start - Welcome message\n/help - This message\n\nPapers are fetched from arXiv categories:\ncs.LG, cs.CL, cs.CV, cs.AI, cs.NE, cs.IR, stat.ML",
        "digest_header": "📰 <b>Latest Papers</b>\n\nTap a paper to see summary:",
        "no_papers": "No papers yet. Run the pipeline first!",
        "no_summary": "Summary not available yet.",
        "links": "🔗 Links:",
    },
    "ru": {
        "welcome": "👋 Добро пожаловать в <b>sota-radar</b>!\n\nЯ доставляю AI/ML саммари статей с arXiv.\n\nВыберите язык:",
        "lang_set": "✅ Язык установлен: Русский",
        "onboarding": "🤖 <b>Как пользоваться sota-radar:</b>\n\n📰 /digest — Смотреть последние AI/ML статьи\n   Нажмите на статью для просмотра саммари\n\n🌐 /language — Сменить язык\n\n📚 /help — Полный список команд\n\n<i>Статьи обновляются каждые 5 минут с arXiv.</i>",
        "help": "📚 <b>Справка sota-radar</b>\n\n/digest - Показать последние статьи с AI-саммари\n/language - Изменить язык\n/start - Приветствие\n/help - Эта справка\n\nСтатьи из категорий arXiv:\ncs.LG, cs.CL, cs.CV, cs.AI, cs.NE, cs.IR, stat.ML",
        "digest_header": "📰 <b>Последние статьи</b>\n\nНажмите на статью для просмотра саммари:",
        "no_papers": "Статей пока нет. Запустите пайплайн!",
        "no_summary": "Саммари ещё не готово.",
        "links": "🔗 Ссылки:",
    },
}


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
    init_db()
    session = get_session()
    user_repo = UserRepository(session)
    lang = user_repo.get_language(message.from_user.id)
    session.close()

    await message.answer(
        get_text("welcome", lang),
        parse_mode="HTML",
        reply_markup=get_language_keyboard(),
    )


@router.message(Command("language"))
async def cmd_language(message: Message):
    """Handle /language command."""
    init_db()
    session = get_session()
    user_repo = UserRepository(session)
    lang = user_repo.get_language(message.from_user.id)
    session.close()

    await message.answer(
        get_text("welcome", lang),
        parse_mode="HTML",
        reply_markup=get_language_keyboard(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def callback_language(callback: CallbackQuery):
    """Handle language selection callback."""
    lang = callback.data.split(":")[1]
    
    init_db()
    session = get_session()
    user_repo = UserRepository(session)
    user_repo.set_language(callback.from_user.id, lang)
    session.close()

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
    init_db()
    session = get_session()
    user_repo = UserRepository(session)
    lang = user_repo.get_language(message.from_user.id)
    session.close()

    await message.answer(
        get_text("help", lang),
        parse_mode="HTML",
    )


@router.message(Command("digest"))
async def cmd_digest(message: Message):
    """Handle /digest command - show papers as inline buttons."""
    init_db()
    session = get_session()
    repo = PaperRepository(session)
    user_repo = UserRepository(session)
    lang = user_repo.get_language(message.from_user.id)

    # Get recent papers
    papers = repo.get_recent(limit=10)
    session.close()

    if not papers:
        await message.answer(get_text("no_papers", lang))
        return

    # Build inline keyboard with paper titles
    buttons = []
    for paper in papers:
        title = paper.title[:60] + "..." if len(paper.title) > 60 else paper.title
        buttons.append([
            InlineKeyboardButton(
                text=title,
                callback_data=f"paper:{paper.id}",
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        get_text("digest_header", lang),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("paper:"))
async def callback_paper(callback: CallbackQuery):
    """Handle paper selection callback - show full summary."""
    paper_id = int(callback.data.split(":")[1])
    
    init_db()
    session = get_session()
    repo = PaperRepository(session)
    user_repo = UserRepository(session)
    lang = user_repo.get_language(callback.from_user.id)
    
    paper = repo.get_by_id(paper_id)
    session.close()

    if not paper:
        await callback.answer("Paper not found", show_alert=True)
        return

    await callback.answer()

    # Parse summary JSON
    if paper.summary_json:
        try:
            summaries = json.loads(paper.summary_json)
            summary = summaries.get(lang, summaries.get("en", get_text("no_summary", lang)))
        except json.JSONDecodeError:
            summary = paper.summary_json  # Fallback for old plain text
    else:
        summary = get_text("no_summary", lang)

    # Build response
    title = html.escape(paper.title)
    summary = html.escape(summary)
    
    response = (
        f"<b>{title}</b>\n\n"
        f"📝 {summary}\n\n"
        f"{get_text('links', lang)}\n"
        f"• <a href=\"{paper.url}\">arXiv</a>\n"
        f"• <a href=\"{paper.pdf_url}\">PDF</a>"
    )

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
    )
    _summary_messages[user_id] = sent_message.message_id


def register_handlers(dp: Dispatcher):
    """Register all handlers with dispatcher."""
    dp.include_router(router)

