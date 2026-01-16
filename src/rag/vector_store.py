"""ChromaDB vector store for paper chunks."""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config.settings import settings
from src.rag.embeddings import EmbeddingModel

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB vector store for paper chunks.
    
    Uses persistent storage for data durability across restarts.
    Each paper's chunks are stored with paper_id metadata for filtering.
    """
    
    _instance: Optional["VectorStore"] = None
    _client: Optional[chromadb.PersistentClient] = None
    _collection: Optional[chromadb.Collection] = None

    def __new__(cls) -> "VectorStore":
        """Singleton pattern for shared ChromaDB connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize vector store."""
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        self.persist_dir = str(
            getattr(settings, "CHROMA_PERSIST_DIR", settings.DATA_DIR / "chroma")
        )
        self.collection_name = "papers"
        self._embedding_model = EmbeddingModel()

    @property
    def client(self) -> chromadb.PersistentClient:
        """Get or create ChromaDB client."""
        if VectorStore._client is None:
            logger.info(f"Initializing ChromaDB at: {self.persist_dir}")
            VectorStore._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        return VectorStore._client

    @property
    def collection(self) -> chromadb.Collection:
        """Get or create papers collection."""
        if VectorStore._collection is None:
            VectorStore._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Using collection '{self.collection_name}' with {self.collection.count()} documents")
        return VectorStore._collection

    @property
    def abstracts_collection(self) -> chromadb.Collection:
        """Get or create abstracts collection."""
        if not hasattr(self, "_abstracts_collection") or self._abstracts_collection is None:
            self._abstracts_collection = self.client.get_or_create_collection(
                name="abstracts",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Using collection 'abstracts' with {self._abstracts_collection.count()} documents")
        return self._abstracts_collection

    def add_abstract(self, paper_id: str, title: str, abstract: str) -> bool:
        """Add paper abstract to abstracts collection.
        
        Args:
            paper_id: Unique paper identifier.
            title: Paper title.
            abstract: Abstract text.
        """
        if not abstract:
            return False
            
        # Generate embedding
        embedding = self._embedding_model.embed_single(abstract)
        
        self.abstracts_collection.add(
            ids=[paper_id],
            embeddings=[embedding],
            documents=[abstract],
            metadatas=[{"paper_id": paper_id, "title": title}]
        )
        return True

    def add_paper_chunks(
        self,
        paper_id: str,
        chunks: list[str],
        metadata: Optional[dict] = None
    ) -> int:
        """Add paper chunks with embeddings to the store.
        
        Args:
            paper_id: Unique paper identifier (e.g., arXiv ID).
            chunks: List of text chunks.
            metadata: Additional metadata to store with each chunk.
            
        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0
        
        logger.info(f"Adding {len(chunks)} chunks for paper {paper_id}")
        
        # Generate embeddings
        embeddings = self._embedding_model.embed(chunks)
        
        # Prepare document IDs and metadata
        ids = [f"{paper_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = []
        
        base_metadata = metadata or {}
        for i in range(len(chunks)):
            chunk_meta = {
                "paper_id": paper_id,
                "chunk_index": i,
                **base_metadata
            }
            metadatas.append(chunk_meta)
        
        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        
        logger.info(f"Added {len(chunks)} chunks to collection")
        return len(chunks)

    def query(
        self,
        query_text: str,
        paper_id: Optional[str] = None,
        n_results: int = 5
    ) -> list[dict]:
        """Query similar chunks.
        
        Args:
            query_text: Query text to find similar chunks.
            paper_id: Optional paper ID to filter results.
            n_results: Number of results to return.
            
        Returns:
            List of dicts with 'text', 'metadata', 'distance' keys.
        """
        logger.debug(f"Querying with: '{query_text[:50]}...'")
        
        # Generate query embedding
        query_embedding = self._embedding_model.embed_single(query_text)
        
        # Build filter if paper_id specified
        where_filter = {"paper_id": paper_id} if paper_id else None
        
        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0
                })
        
        logger.debug(f"Found {len(formatted)} results")
        return formatted

    def paper_exists(self, paper_id: str) -> bool:
        """Check if paper is already indexed.
        
        Args:
            paper_id: Paper identifier to check.
            
        Returns:
            True if paper has chunks in the store.
        """
        results = self.collection.get(
            where={"paper_id": paper_id},
            limit=1,
            include=[]
        )
        return len(results["ids"]) > 0

    def delete_paper(self, paper_id: str) -> int:
        """Delete all chunks for a paper.
        
        Args:
            paper_id: Paper identifier.
            
        Returns:
            Number of chunks deleted.
        """
        # Get all chunk IDs for this paper
        results = self.collection.get(
            where={"paper_id": paper_id},
            include=[]
        )
        
        if not results["ids"]:
            return 0
        
        self.collection.delete(ids=results["ids"])
        logger.info(f"Deleted {len(results['ids'])} chunks for paper {paper_id}")
        return len(results["ids"])

    def get_stats(self) -> dict:
        """Get collection statistics.
        
        Returns:
            Dict with 'total_chunks' and 'unique_papers' keys.
        """
        total = self.collection.count()
        
        # Get unique paper IDs
        if total > 0:
            results = self.collection.get(include=["metadatas"])
            paper_ids = set()
            for meta in results.get("metadatas", []):
                if meta and "paper_id" in meta:
                    paper_ids.add(meta["paper_id"])
            unique_papers = len(paper_ids)
        else:
            unique_papers = 0
        
        return {
            "total_chunks": total,
            "unique_papers": unique_papers
        }
