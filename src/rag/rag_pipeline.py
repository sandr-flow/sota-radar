"""RAG pipeline for deep paper analysis."""

import asyncio
import logging
from pathlib import Path

import yaml

from src.config.settings import settings
from src.llm import get_provider
from src.rag.pdf_extractor import PDFExtractor
from src.rag.chunker import SemanticChunker
from src.rag.vector_store import VectorStore
from src.storage import get_session, PaperRepository

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG pipeline for deep paper analysis.
    
    Orchestrates PDF extraction, chunking, indexing, and LLM analysis.
    """

    def __init__(self):
        """Initialize RAG pipeline components."""
        self.pdf_extractor = PDFExtractor()
        self.chunker = SemanticChunker(
            max_chunk_size=getattr(settings, "CHUNK_SIZE", 512),
            min_chunk_size=100,
            overlap_sentences=1
        )
        self.vector_store = VectorStore()
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        """Load prompts from YAML config."""
        prompts_path = settings.BASE_DIR / "config" / "prompts.yaml"
        with open(prompts_path, encoding="utf-8") as f:
            return yaml.safe_load(f).get("prompts", {})

    async def index_paper(self, paper_id: int) -> bool:
        """Download, extract, chunk, and index a paper.
        
        Args:
            paper_id: Database paper ID.
            
        Returns:
            True if successfully indexed, False otherwise.
        """
        # Get paper from database
        session = get_session()
        repo = PaperRepository(session)
        paper = await asyncio.to_thread(repo.get_by_id, paper_id)
        session.close()
        
        if not paper:
            logger.error(f"Paper {paper_id} not found")
            return False
        
        # Check if already indexed
        if self.vector_store.paper_exists(paper.source_id):
            logger.info(f"Paper {paper.source_id} already indexed")
            return True
        
        # Download and extract PDF
        if not paper.pdf_url:
            logger.error(f"No PDF URL for paper {paper_id}")
            return False
        
        try:
            full_text = await self.pdf_extractor.download_and_extract(paper.pdf_url)
        except Exception as e:
            logger.error(f"Failed to extract PDF: {e}")
            return False
        
        if len(full_text) < 100:
            logger.error(f"Extracted text too short ({len(full_text)} chars)")
            return False
        
        # Chunk the text
        chunks = self.chunker.get_chunk_texts(full_text)
        
        if not chunks:
            logger.error("No chunks generated")
            return False
        
        # Index chunks
        metadata = {
            "source": paper.source,
            "title": paper.title[:200],  # Truncate for metadata
            "db_id": paper_id
        }
        
        self.vector_store.add_paper_chunks(
            paper_id=paper.source_id,
            chunks=chunks,
            metadata=metadata
        )
        
        logger.info(f"Successfully indexed paper {paper.source_id} with {len(chunks)} chunks")
        return True

    async def answer_question(
        self,
        paper_id: int,
        prompt_key: str
    ) -> dict[str, str]:
        """Answer a specific question about a paper using RAG.
        
        Args:
            paper_id: Database paper ID.
            prompt_key: Key of the prompt in prompts.yaml (e.g., 'rag_essence').
            
        Returns:
            Dict with 'en' and 'ru' keys containing the answer.
        """
        # Ensure paper is indexed
        indexed = await self.index_paper(paper_id)
        if not indexed:
            return {
                "en": "Failed to index paper.",
                "ru": "Не удалось проиндексировать статью."
            }
        
        # Get paper info
        session = get_session()
        repo = PaperRepository(session)
        paper = await asyncio.to_thread(repo.get_by_id, paper_id)
        session.close()
        
        if not paper:
            return {
                "en": "Paper not found.",
                "ru": "Статья не найдена."
            }
        
        # Retrieve relevant chunks
        results = self.vector_store.query(
            query_text=paper.title,
            paper_id=paper.source_id,
            n_results=5
        )
        
        if not results:
            return {
                "en": "No relevant content found.",
                "ru": "Релевантный контент не найден."
            }
        
        # Build context from retrieved chunks
        context = "\n\n".join([r["text"][:500] for r in results])  # Limit chunk size
        
        # Get prompt template
        prompt_template = self._prompts.get(prompt_key)
        if not prompt_template:
            return {
                "en": f"Prompt '{prompt_key}' not found.",
                "ru": f"Промпт '{prompt_key}' не найден."
            }
        
        prompt = prompt_template.format(context=context)
        
        try:
            import json
            from src.infrastructure.http_client import get_client
            from src.llm.rate_limiter import MISTRAL_RATE_LIMITER
            
            MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
            provider = get_provider()
            
            await MISTRAL_RATE_LIMITER.acquire()
            
            headers = {
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": provider.model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            }
            
            client = get_client()
            response = await client.post(
                MISTRAL_API_URL,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            answer = json.loads(content)
            
            if "en" not in answer or "ru" not in answer:
                raise ValueError("Missing required language keys")
            
            return answer
            
        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            return {
                "en": f"Error: {str(e)[:100]}",
                "ru": f"Ошибка: {str(e)[:100]}"
            }

    async def analyze_paper_questions(
        self,
        paper_id: int
    ) -> list[dict[str, str]]:
        """Run 3-question RAG analysis on a paper.
        
        Args:
            paper_id: Database paper ID.
            
        Returns:
            List of 3 dicts with 'en' and 'ru' keys for each question.
        """
        questions = ["rag_essence", "rag_importance", "rag_applications"]
        results = []
        
        for prompt_key in questions:
            answer = await self.answer_question(paper_id, prompt_key)
            results.append(answer)
        
        return results

