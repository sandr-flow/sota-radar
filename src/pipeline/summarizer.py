"""Background summarization pipeline for sota-radar."""

import asyncio
import logging
from datetime import datetime

from src.llm import get_provider
from src.storage import get_session, init_db, PaperRepository

logger = logging.getLogger(__name__)


async def summarize_papers(batch_size: int = 10) -> tuple[int, int]:
    """Summarize unsummarized papers in database (bilingual EN + RU).

    Rate limiting is handled by the LLM provider (1 RPS for Mistral free tier).
    Each paper requires 2 API calls: summarize (EN) + translate (RU).

    Args:
        batch_size: Number of papers to process in one run.

    Returns:
        Tuple of (success_count, error_count).
    """
    # Initialize
    init_db()
    session = get_session()
    repo = PaperRepository(session)
    provider = get_provider()

    # Get unsummarized papers
    papers = repo.get_unsummarized(limit=batch_size)
    logger.info(f"Found {len(papers)} unsummarized papers")

    success = 0
    errors = 0

    for paper in papers:
        try:
            logger.info(f"Summarizing: {paper.source_id} - {paper.title[:50]}...")

            # Generate English summary (rate limited by provider)
            summary_en = await provider.summarize(paper.abstract)
            logger.info(f"  EN summary generated")

            # Translate to Russian
            summary_ru = await provider.translate(summary_en, target_language="ru")
            logger.info(f"  RU translation generated")

            # Save bilingual summary as JSON
            summary_dict = {"en": summary_en, "ru": summary_ru}
            repo.update_summary(paper.id, summary_dict)

            success += 1
            logger.info(f"✓ Summarized {paper.source_id}")

        except Exception as e:
            errors += 1
            logger.error(f"✗ Failed {paper.source_id}: {e}")

    session.close()
    logger.info(f"Completed: {success} success, {errors} errors")
    return success, errors


async def run_full_pipeline(
    categories: list[str] | None = None,
    max_per_category: int = 20,
    summarize_batch: int = 10,
) -> dict:
    """Run full pipeline: fetch papers, store, summarize.

    Args:
        categories: List of arXiv categories. Uses config if None.
        max_per_category: Max papers to fetch per category.
        summarize_batch: Number of papers to summarize.

    Returns:
        Stats dict with fetched, stored, summarized counts.
    """
    from src.config import load_config
    from src.sources.arxiv import ArxivSource

    # Load config
    config = load_config()
    if categories is None:
        categories = [c.id for c in config.categories]

    # Initialize storage
    init_db()
    session = get_session()
    repo = PaperRepository(session)

    # Fetch and store papers
    source = ArxivSource()
    total_added = 0
    total_skipped = 0

    for category in categories:
        logger.info(f"Fetching from {category}...")
        papers = await source.fetch_papers(category=category, max_results=max_per_category)
        added, skipped = repo.add_many(papers)
        total_added += added
        total_skipped += skipped
        logger.info(f"  Added: {added}, Skipped: {skipped}")

    session.close()

    # Summarize new papers
    success, errors = await summarize_papers(batch_size=summarize_batch)

    return {
        "fetched_categories": len(categories),
        "papers_added": total_added,
        "papers_skipped": total_skipped,
        "summarized": success,
        "summary_errors": errors,
    }
