"""Telegram bot for sota-radar."""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from src.config.settings import settings
from src.bot.handlers import register_handlers
from src.pipeline.summarizer import background_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Start the bot with background pipeline."""
    token = settings.TELEGRAM_BOT_TOKEN
    
    bot = Bot(token=token)
    dp = Dispatcher()

    # Register handlers
    register_handlers(dp)

    # Start background pipeline task
    # Note: background_pipeline is now imported from pipeline module
    asyncio.create_task(background_pipeline())
    logger.info(f"📡 Background pipeline started (interval: {settings.PIPELINE_INTERVAL_MINUTES}min)")

    logger.info("Starting sota-radar bot...")
    try:
        await dp.start_polling(bot)
    finally:
        from src.infrastructure.http_client import close_client
        await close_client()
        logger.info("👋 Bot shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
