"""Embedding model wrapper for RAG pipeline."""

import logging
from typing import Optional

from sentence_transformers import SentenceTransformer

from src.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Sentence-transformers embedding model with lazy loading.
    
    Uses all-mpnet-base-v2 by default for high-quality embeddings.
    Model is loaded on first use to avoid startup delay.
    """
    
    _instance: Optional["EmbeddingModel"] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls) -> "EmbeddingModel":
        """Singleton pattern for model reuse."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize embedding model wrapper."""
        self.model_name = getattr(settings, "EMBEDDING_MODEL", "all-mpnet-base-v2")

    @property
    def model(self) -> SentenceTransformer:
        """Get or load the embedding model (lazy loading)."""
        if EmbeddingModel._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            # Use local_files_only to skip huggingface.co checks if model cached
            local_only = getattr(settings, "EMBEDDING_OFFLINE_MODE", False)
            try:
                EmbeddingModel._model = SentenceTransformer(
                    self.model_name,
                    local_files_only=local_only
                )
            except Exception as e:
                if local_only:
                    logger.warning(f"Offline load failed, trying online: {e}")
                    EmbeddingModel._model = SentenceTransformer(self.model_name)
                else:
                    raise
            logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")
        return EmbeddingModel._model

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of embedding vectors (as lists of floats).
        """
        if not texts:
            return []
        
        logger.debug(f"Embedding {len(texts)} texts...")
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        # Convert numpy arrays to lists for JSON serialization
        return embeddings.tolist()

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text string to embed.
            
        Returns:
            Embedding vector as list of floats.
        """
        return self.embed([text])[0]
