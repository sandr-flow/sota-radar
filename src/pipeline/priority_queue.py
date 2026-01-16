"""Priority queue for on-demand paper summarization.

Uses SQLite-backed persistence to survive bot restarts.
"""

import asyncio
import logging

from src.llm import get_provider
from src.storage import session_scope, PaperRepository

logger = logging.getLogger(__name__)


def add_to_priority_queue(paper_id: int) -> bool:
    """Add paper to priority summarization queue.

    Args:
        paper_id: Database ID of paper to summarize.

    Returns:
        True if added, False if already in queue or has summary.
    """
    with session_scope() as session:
        repo = PaperRepository(session)
        paper = repo.get_by_id(paper_id)
        
        if paper is None:
            return False
        
        # Already has summary - no need to queue
        if paper.summary_json:
            return False
        
        # Already in queue
        if paper.priority_requested:
            return False
        
        added = repo.mark_priority(paper_id)
        if added:
            logger.info(f"📋 Added paper {paper_id} to priority queue")
        return added


def is_in_queue(paper_id: int) -> bool:
    """Check if paper is in priority queue.
    
    Args:
        paper_id: Database ID of paper.
        
    Returns:
        True if paper is marked for priority processing.
    """
    with session_scope() as session:
        repo = PaperRepository(session)
        paper = repo.get_by_id(paper_id)
        return paper is not None and paper.priority_requested


def queue_size() -> int:
    """Get current priority queue size.
    
    Returns:
        Number of papers waiting for priority summarization.
    """
    with session_scope() as session:
        repo = PaperRepository(session)
        papers = repo.get_priority_papers(limit=1000)
        return len(papers)


async def process_priority_queue() -> tuple[int, int]:
    """Process all papers in priority queue.

    Returns:
        Tuple of (success_count, error_count).
    """
    with session_scope() as session:
        repo = PaperRepository(session)
        priority_papers = repo.get_priority_papers(limit=100)
        
        if not priority_papers:
            return 0, 0
        
        logger.info(f"🔥 Processing {len(priority_papers)} priority papers")
        
        provider = get_provider()
        success = 0
        errors = 0
        
        for paper in priority_papers:
            try:
                # Skip if already summarized (race condition protection)
                if paper.summary_json:
                    repo.clear_priority(paper.id)
                    continue
                
                logger.info(f"🔥 Priority summarizing: {paper.source_id} - {paper.title[:40]}...")
                
                # Generate bilingual summary
                summary_dict = await provider.generate_bilingual_summary(paper.abstract)
                
                # Save to DB
                await asyncio.to_thread(repo.update_summary, paper.id, summary_dict)
                
                # Clear priority flag
                await asyncio.to_thread(repo.clear_priority, paper.id)
                
                success += 1
                logger.info(f"✓ Priority summarized {paper.source_id}")
                
            except Exception as e:
                errors += 1
                logger.error(f"✗ Priority summarization failed for {paper.id}: {e}")
                # Clear priority on persistent errors to avoid infinite retries
                # User can re-request if needed
                await asyncio.to_thread(repo.clear_priority, paper.id)
        
        return success, errors
