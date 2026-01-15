"""Test script for RAG pipeline components."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_pdf_extraction():
    """Test PDF download and text extraction."""
    from src.rag.pdf_extractor import PDFExtractor
    
    logger.info("=" * 50)
    logger.info("Testing PDF Extraction")
    logger.info("=" * 50)
    
    # Use a known arXiv paper
    test_url = "https://arxiv.org/pdf/2301.00234.pdf"
    
    extractor = PDFExtractor()
    
    try:
        text = await extractor.download_and_extract(test_url)
        logger.info(f"Extracted {len(text)} characters")
        logger.info(f"First 500 chars:\n{text[:500]}...")
        return True
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return False


def test_chunking():
    """Test semantic chunking."""
    from src.rag.chunker import SemanticChunker
    
    logger.info("=" * 50)
    logger.info("Testing Semantic Chunking")
    logger.info("=" * 50)
    
    chunker = SemanticChunker(max_chunk_size=300, min_chunk_size=50)
    
    sample_text = """
    Abstract
    
    This paper presents a novel approach to machine learning that combines
    transformer architectures with reinforcement learning. Our method achieves
    state-of-the-art results on multiple benchmarks.
    
    1. Introduction
    
    Machine learning has seen tremendous progress in recent years. The introduction
    of transformer architectures has revolutionized natural language processing
    and computer vision. However, challenges remain in combining these architectures
    with reinforcement learning paradigms.
    
    2. Methodology
    
    We propose a hybrid architecture that integrates self-attention mechanisms
    with policy gradient methods. The key innovation is our attention-guided
    reward shaping technique that improves sample efficiency.
    
    3. Experiments
    
    We evaluate our approach on Atari games and robotic manipulation tasks.
    Results show significant improvements over baseline methods.
    """
    
    chunks = chunker.chunk_text(sample_text)
    
    logger.info(f"Created {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        logger.info(f"Chunk {i}: {len(chunk.text)} chars")
        logger.info(f"  Preview: {chunk.text[:100]}...")
    
    return len(chunks) > 0


def test_embeddings():
    """Test embedding model."""
    from src.rag.embeddings import EmbeddingModel
    
    logger.info("=" * 50)
    logger.info("Testing Embeddings (all-mpnet-base-v2)")
    logger.info("=" * 50)
    
    model = EmbeddingModel()
    
    texts = [
        "Machine learning is transforming AI research.",
        "Deep learning uses neural networks.",
        "Cats are popular pets.",
    ]
    
    embeddings = model.embed(texts)
    
    logger.info(f"Embedding dimension: {model.embedding_dim}")
    logger.info(f"Generated {len(embeddings)} embeddings")
    
    # Check similarity
    import numpy as np
    e1, e2, e3 = embeddings
    sim_12 = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
    sim_13 = np.dot(e1, e3) / (np.linalg.norm(e1) * np.linalg.norm(e3))
    
    logger.info(f"Similarity (ML, DL): {sim_12:.4f}")
    logger.info(f"Similarity (ML, Cats): {sim_13:.4f}")
    
    return sim_12 > sim_13  # ML should be more similar to DL than to cats


def test_vector_store():
    """Test ChromaDB vector store."""
    from src.rag.vector_store import VectorStore
    
    logger.info("=" * 50)
    logger.info("Testing ChromaDB Vector Store")
    logger.info("=" * 50)
    
    store = VectorStore()
    
    # Clean up test data
    store.delete_paper("test_paper_123")
    
    # Add test chunks
    test_chunks = [
        "Transformers use self-attention mechanisms.",
        "BERT is a bidirectional transformer model.",
        "GPT uses autoregressive language modeling.",
    ]
    
    added = store.add_paper_chunks(
        paper_id="test_paper_123",
        chunks=test_chunks,
        metadata={"source": "test", "title": "Test Paper"}
    )
    
    logger.info(f"Added {added} chunks")
    
    # Query
    results = store.query(
        query_text="attention mechanism in neural networks",
        paper_id="test_paper_123",
        n_results=2
    )
    
    logger.info(f"Query results: {len(results)}")
    for r in results:
        logger.info(f"  - {r['text'][:50]}... (distance: {r['distance']:.4f})")
    
    # Cleanup
    store.delete_paper("test_paper_123")
    
    return len(results) > 0


async def main():
    """Run all tests."""
    logger.info("Starting RAG Pipeline Tests")
    logger.info("=" * 60)
    
    results = {}
    
    # Test chunking (no deps)
    results["chunking"] = test_chunking()
    
    # Test embeddings (requires sentence-transformers)
    try:
        results["embeddings"] = test_embeddings()
    except ImportError as e:
        logger.warning(f"Skipping embeddings test (missing dependency): {e}")
        results["embeddings"] = None
    
    # Test vector store (requires chromadb)
    try:
        results["vector_store"] = test_vector_store()
    except ImportError as e:
        logger.warning(f"Skipping vector store test (missing dependency): {e}")
        results["vector_store"] = None
    
    # Test PDF extraction (requires pymupdf)
    try:
        results["pdf_extraction"] = await test_pdf_extraction()
    except ImportError as e:
        logger.warning(f"Skipping PDF test (missing dependency): {e}")
        results["pdf_extraction"] = None
    
    # Summary
    logger.info("=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        if passed is None:
            status = "⏭️ SKIPPED"
        elif passed:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        logger.info(f"  {test_name}: {status}")


if __name__ == "__main__":
    asyncio.run(main())
