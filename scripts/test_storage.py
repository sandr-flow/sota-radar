"""Test script to verify storage and deduplication."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config
from src.sources.arxiv import ArxivSource
from src.storage import get_session, init_db, PaperRepository


async def main():
    """Fetch papers and store them with deduplication."""
    # Initialize database
    init_db()
    session = get_session()
    repo = PaperRepository(session)

    print(f"Papers in database before: {repo.count()}")

    # Load config and fetch papers
    config = load_config()
    source = ArxivSource()

    category = config.categories[0]  # cs.LG
    print(f"\nFetching from {category.id}...")
    papers = await source.fetch_papers(category=category.id, max_results=10)
    print(f"Fetched {len(papers)} papers from arXiv")

    # Store with deduplication
    added, skipped = repo.add_many(papers)
    print(f"Added: {added}, Skipped (duplicates): {skipped}")

    print(f"\nPapers in database after: {repo.count()}")

    # Show recent papers
    print("\n--- Recent papers in DB ---")
    for paper in repo.get_recent(5):
        print(f"- [{paper.source}:{paper.source_id}] {paper.title[:60]}...")

    session.close()


if __name__ == "__main__":
    asyncio.run(main())
