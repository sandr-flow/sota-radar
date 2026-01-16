"""Priority queue for on-demand paper summarization."""

import asyncio
import logging
from collections import deque
from typing import Set

from src.llm import get_provider
from src.storage import session_scope, PaperRepository

logger = logging.getLogger(__name__)

# Priority queue for papers requested by users
# These will be summarized before regular background batch
_priority_queue: deque[int] = deque()  # Paper IDs
_processing: Set[int] = set()  # Currently being processed


def add_to_priority_queue(paper_id: int) -> bool:
    """Add paper to priority summarization queue.

    Args:
        paper_id: Database ID of paper to summarize.

    Returns:
        True if added, False if already in queue or processing.
    """
    if paper_id in _priority_queue or paper_id in _processing:
        return False
    
    _priority_queue.append(paper_id)
    logger.info(f"📋 Added paper {paper_id} to priority queue (queue size: {len(_priority_queue)})")
    return True


def get_next_priority() -> int | None:
    """Get next paper ID from priority queue.

    Returns:
        Paper ID or None if queue is empty.
    """
    if not _priority_queue:
        return None
    
    paper_id = _priority_queue.popleft()
    _processing.add(paper_id)
    return paper_id


def mark_completed(paper_id: int) -> None:
    """Mark paper as completed (remove from processing set)."""
    _processing.discard(paper_id)


def is_in_queue(paper_id: int) -> bool:
    """Check if paper is in queue or being processed."""
    return paper_id in _priority_queue or paper_id in _processing


def queue_size() -> int:
    """Get current queue size."""
    return len(_priority_queue)


async def process_priority_queue() -> tuple[int, int]:
    """Process all papers in priority queue.

    Returns:
        Tuple of (success_count, error_count).
    """
    if not _priority_queue and not _processing:
        return 0, 0

    provider = get_provider()
    success = 0
    errors = 0

    with session_scope() as session:
        repo = PaperRepository(session)

        while True:
            paper_id = get_next_priority()
            if paper_id is None:
                break

            try:
                paper = await asyncio.to_thread(repo.get_by_id, paper_id)
                if not paper:
                    logger.warning(f"Paper {paper_id} not found in DB")
                    mark_completed(paper_id)
                    continue

                if paper.summary_json:
                    logger.info(f"Paper {paper_id} already has summary, skipping")
                    mark_completed(paper_id)
                    continue

                logger.info(f"🔥 Priority summarizing: {paper.source_id} - {paper.title[:40]}...")

                # Generate bilingual summary
                summary_dict = await provider.generate_bilingual_summary(paper.abstract)
                
                # Save to DB
                await asyncio.to_thread(repo.update_summary, paper.id, summary_dict)

                success += 1
                logger.info(f"✓ Priority summarized {paper.source_id}")

            except Exception as e:
                errors += 1
                logger.error(f"✗ Priority summarization failed for {paper_id}: {e}")
            finally:
                mark_completed(paper_id)

    return success, errors
