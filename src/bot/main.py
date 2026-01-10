"""Telegram bot for sota-radar."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.handlers import register_handlers
from src.pipeline.summarizer import run_full_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Pipeline settings
PIPELINE_INTERVAL_MINUTES = 5


async def background_pipeline():
    """Run summarization pipeline periodically in background.
    
    Runs immediately on startup, then every PIPELINE_INTERVAL_MINUTES.
    """
    while True:
        try:
            logger.info("🚀 Starting background pipeline run...")
            stats = await run_full_pipeline()
            logger.info(
                f"✅ Pipeline completed: "
                f"added={stats['papers_added']}, "
                f"summarized={stats['summarized']}, "
                f"errors={stats['summary_errors']}"
            )
        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}")
        
        await asyncio.sleep(PIPELINE_INTERVAL_MINUTES * 60)


async def main():
    """Start the bot with background pipeline."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    bot = Bot(token=token)
    dp = Dispatcher()

    # Register handlers
    register_handlers(dp)

    # Start background pipeline task
    asyncio.create_task(background_pipeline())
    logger.info(f"📡 Background pipeline started (interval: {PIPELINE_INTERVAL_MINUTES}min)")

    logger.info("Starting sota-radar bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
