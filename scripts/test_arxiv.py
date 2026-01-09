"""Test script to verify arXiv parser with config loading."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config
from src.sources.arxiv import ArxivSource


async def main():
    """Fetch papers from all configured categories."""
    config = load_config()
    source = ArxivSource()

    print(f"Source: {source.source_name}")
    print(f"Configured categories: {len(config.categories)}")
    print(f"Max results per category: {config.settings.max_results_per_category}")
    print(f"Papers per digest: {config.settings.papers_per_digest}")
    print()

    # Fetch from first category as demo
    category = config.categories[0]
    print(f"Fetching from {category.id} ({category.name})...")
    papers = await source.fetch_papers(
        category=category.id,
        max_results=5,
    )

    print(f"Fetched {len(papers)} papers\n")

    for i, paper in enumerate(papers, 1):
        print(f"--- Paper {i} ---")
        print(f"ID: {paper.unique_id}")
        print(f"Title: {paper.title[:80]}...")
        print(f"Authors: {', '.join(paper.authors[:3])}...")
        print(f"Published: {paper.published}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
