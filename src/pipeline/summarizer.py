"""Background summarization pipeline for sota-radar."""

import asyncio
import logging
from datetime import datetime

from src.config.settings import settings
from src.llm import get_provider
from src.storage import session_scope, PaperRepository

logger = logging.getLogger(__name__)


async def background_pipeline():
    """Run summarization pipeline periodically in background.
    
    Runs immediately on startup, then every PIPELINE_INTERVAL_MINUTES.
    Priority queue is checked more frequently.
    """
    from src.pipeline.priority_queue import process_priority_queue, queue_size
    
    while True:
        try:
            # First, process priority queue (user-requested papers)
            if queue_size() > 0:
                logger.info(f"🔥 Processing priority queue ({queue_size()} papers)...")
                p_success, p_errors = await process_priority_queue()
                if p_success > 0 or p_errors > 0:
                    logger.info(f"🔥 Priority queue: {p_success} success, {p_errors} errors")
            
            # Then run regular pipeline
            logger.info("🚀 Starting background pipeline run...")
            stats = await run_full_pipeline()
            logger.info(
                f"✅ Pipeline completed: "
                f"added={stats['papers_added']}, "
                f"summarized={stats['summarized']}, "
                f"errors={stats['summary_errors']}"
            )
        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}", exc_info=True)
        
        # Check priority queue more often (every 30 seconds)
        # but only run full pipeline every PIPELINE_INTERVAL_MINUTES
        for _ in range(settings.PIPELINE_INTERVAL_MINUTES * 2):
            await asyncio.sleep(30)
            # Process priority queue if any
            if queue_size() > 0:
                logger.info(f"🔥 Processing priority queue ({queue_size()} papers)...")
                p_success, p_errors = await process_priority_queue()
                if p_success > 0 or p_errors > 0:
                    logger.info(f"🔥 Priority queue: {p_success} success, {p_errors} errors")



async def summarize_papers(batch_size: int = 10) -> tuple[int, int]:
    """Summarize unsummarized papers in database (bilingual EN + RU).

    Rate limiting is handled by the LLM provider (1 RPS for Mistral free tier).
    Each paper requires 2 API calls: summarize (EN) + translate (RU).

    Args:
        batch_size: Number of papers to process in one run.

    Returns:
        Tuple of (success_count, error_count).
    """
    provider = get_provider()
    
    with session_scope() as session:
        repo = PaperRepository(session)

        # Get unsummarized papers (run in thread to avoid blocking)
        papers = await asyncio.to_thread(repo.get_unsummarized, limit=batch_size)
        logger.info(f"Found {len(papers)} unsummarized papers")

        success = 0
        errors = 0

        for paper in papers:
            try:
                logger.info(f"Summarizing: {paper.source_id} - {paper.title[:50]}...")

                # Generate bilingual summary in one call (rate limited by provider)
                summary_dict = await provider.generate_bilingual_summary(paper.abstract)
                logger.info(f"  Bilingual summary generated (EN + RU)")

                # Save bilingual summary as JSON (run in thread)
                await asyncio.to_thread(repo.update_summary, paper.id, summary_dict)

                success += 1
                logger.info(f"✓ Summarized {paper.source_id}")

            except Exception as e:
                errors += 1
                logger.error(f"✗ Failed {paper.source_id}: {e}")

    logger.info(f"Completed: {success} success, {errors} errors")
    return success, errors


async def run_full_pipeline(
    categories: list[str] | None = None,
    max_per_category: int | None = None,
    summarize_batch: int | None = None,
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

    if max_per_category is None:
        max_per_category = settings.MAX_RESULTS_PER_CATEGORY
    
    if summarize_batch is None:
        summarize_batch = settings.PAPERS_PER_DIGEST # Use digest size as logical batch default

    # Load config (legacy loader for categories until fully migrated)
    config = load_config()
    if categories is None:
        categories = [c.id for c in config.categories]

    # Fetch and store papers
    source = ArxivSource()
    total_added = 0
    total_skipped = 0

    with session_scope() as session:
        repo = PaperRepository(session)
        
        for category in categories:
            logger.info(f"Fetching from {category}...")
            try:
                papers = await source.fetch_papers(category=category, max_results=max_per_category)
                
                # Run bulk insert in thread to avoid blocking
                added, skipped = await asyncio.to_thread(repo.add_many, papers)
                
                total_added += added
                total_skipped += skipped
                logger.info(f"  Added: {added}, Skipped: {skipped}")
            except Exception as e:
                logger.error(f"Failed to fetch category {category}: {e}")

    # Summarize new papers
    success, errors = await summarize_papers(batch_size=summarize_batch)

    return {
        "fetched_categories": len(categories),
        "papers_added": total_added,
        "papers_skipped": total_skipped,
        "summarized": success,
        "summary_errors": errors,
    }
