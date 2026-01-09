"""Test script to verify arXiv parser works."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sources.arxiv import ArxivSource


async def main():
    """Fetch and display 5 papers from cs.LG category."""
    source = ArxivSource()
    papers = await source.fetch_papers(category="cs.LG", max_results=5)

    print(f"Source: {source.source_name}")
    print(f"Fetched {len(papers)} papers\n")

    for i, paper in enumerate(papers, 1):
        print(f"--- Paper {i} ---")
        print(f"ID: {paper.unique_id}")
        print(f"Title: {paper.title[:80]}...")
        print(f"Authors: {', '.join(paper.authors[:3])}...")
        print(f"Published: {paper.published}")
        print(f"URL: {paper.url}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
