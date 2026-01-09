"""Run the full summarization pipeline."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

from src.pipeline import run_full_pipeline


async def main():
    """Run the full pipeline with limited scope for testing."""
    print("=== sota-radar: Full Pipeline ===\n")

    # Run pipeline with just 2 categories and 5 papers each for testing
    stats = await run_full_pipeline(
        categories=["cs.LG", "cs.CL"],  # Just 2 categories for testing
        max_per_category=5,
        summarize_batch=3,  # Summarize 3 papers
    )

    print("\n=== Pipeline Complete ===")
    print(f"Categories processed: {stats['fetched_categories']}")
    print(f"Papers added: {stats['papers_added']}")
    print(f"Papers skipped (duplicates): {stats['papers_skipped']}")
    print(f"Papers summarized: {stats['summarized']}")
    print(f"Summary errors: {stats['summary_errors']}")


if __name__ == "__main__":
    asyncio.run(main())
