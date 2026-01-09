"""Test script to verify LLM gateway with Mistral."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.llm import get_provider


async def main():
    """Test LLM summarization with a sample abstract."""
    provider = get_provider()
    print(f"Provider: {provider.provider_name}")

    sample_abstract = """
    We present a novel approach to training large language models that 
    significantly reduces computational costs while maintaining performance. 
    Our method combines sparse attention mechanisms with dynamic pruning, 
    achieving 40% reduction in FLOPs with only 2% degradation in benchmark 
    scores. We evaluate on standard NLP benchmarks including GLUE and SuperGLUE, 
    demonstrating state-of-the-art efficiency-accuracy tradeoffs. Our approach 
    enables training of 70B parameter models on consumer hardware.
    """

    print("\n--- Original Abstract ---")
    print(sample_abstract.strip())

    print("\n--- Generating Summary ---")
    summary = await provider.summarize(sample_abstract)
    print(summary)

    print("\n--- Translating to Russian ---")
    translation = await provider.translate(summary, target_language="ru")
    print(translation)


if __name__ == "__main__":
    asyncio.run(main())
