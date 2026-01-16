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
from src.storage import session_scope, PaperRepository

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
        # Get paper from database - extract data inside session scope
        paper_data = None
        with session_scope() as session:
            repo = PaperRepository(session)
            paper = await asyncio.to_thread(repo.get_by_id, paper_id)
            if paper:
                paper_data = {
                    "source_id": paper.source_id,
                    "source": paper.source,
                    "title": paper.title,
                    "pdf_url": paper.pdf_url,
                }
        
        if not paper_data:
            logger.error(f"Paper {paper_id} not found")
            return False
        
        # Check if already indexed
        if self.vector_store.paper_exists(paper_data["source_id"]):
            logger.info(f"Paper {paper_data['source_id']} already indexed")
            return True
        
        # Download and extract PDF
        if not paper_data["pdf_url"]:
            logger.error(f"No PDF URL for paper {paper_id}")
            return False
        
        try:
            full_text = await self.pdf_extractor.download_and_extract(paper_data["pdf_url"])
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
            "source": paper_data["source"],
            "title": paper_data["title"][:200],  # Truncate for metadata
            "db_id": paper_id
        }
        
        self.vector_store.add_paper_chunks(
            paper_id=paper_data["source_id"],
            chunks=chunks,
            metadata=metadata
        )
        
        logger.info(f"Successfully indexed paper {paper_data['source_id']} with {len(chunks)} chunks")
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
        
        # Get paper info - extract data inside session scope
        paper_data = None
        with session_scope() as session:
            repo = PaperRepository(session)
            paper = await asyncio.to_thread(repo.get_by_id, paper_id)
            if paper:
                paper_data = {
                    "title": paper.title,
                    "source_id": paper.source_id,
                }
        
        if not paper_data:
            return {
                "en": "Paper not found.",
                "ru": "Статья не найдена."
            }
        
    
        # Define query based on question type
        query_key = f"{prompt_key}_query"
        query_template = self._prompts.get(query_key, "{title}")
        
        # Format query with paper title
        search_query = query_template.format(title=paper_data["title"])
        
        logger.info(f"🔎 RAG Query ({prompt_key}): '{search_query[:100]}...'")
        
        # Retrieve relevant chunks
        results = self.vector_store.query(
            query_text=search_query,
            paper_id=paper_data["source_id"],
            n_results=5
        )
        
        if not results:
            return {
                "en": "No relevant content found.",
                "ru": "Релевантный контент не найден."
            }
        
        # Enrich context with Abstract of the most relevant paper
        # taking the top 1 paper ID
        top_paper_meta = results[0].get("metadata", {})
        top_paper_source_id = top_paper_meta.get("paper_id") # This is the source_id from the vector store
        
        abstract_text = ""
        if top_paper_source_id:
            try:
                # Fetch abstract from abstracts collection (assuming abstracts are stored with source_id)
                abs_result = self.vector_store.abstracts_collection.get(
                    ids=[top_paper_source_id],
                    include=["documents"]
                )
                if abs_result["documents"]:
                    abstract_doc = abs_result["documents"][0]
                    abstract_text = f"Abstract of {top_paper_meta.get('title', 'Paper')}:\n{abstract_doc}\n\n"
            except Exception as e:
                logger.warning(f"Failed to fetch abstract for {top_paper_source_id}: {e}")

        # Build context from retrieved chunks, including abstract if available
        chunks_text = "\n\n".join([r["text"][:500] for r in results])  # Limit chunk size
        context = f"{abstract_text}Relevant excerpts:\n{chunks_text}"
        
        # Get prompt template
        prompt_template = self._prompts.get(prompt_key)
        if not prompt_template:
            return {
                "en": f"Prompt '{prompt_key}' not found.",
                "ru": f"Промпт '{prompt_key}' не найден."
            }
        
        prompt = prompt_template.format(context=context)
        
        try:
            provider = get_provider()
            answer = await provider.generate_json_response(prompt)
            
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

    async def smart_chat(self, user_message: str) -> str:
        """Handle user chat message with intelligent routing (RAG vs Chat).
        
        Args:
            user_message: User's input message.
            
        Returns:
            Response text (with sources if RAG was used).
        """
        # 1. Router Step
        try:
            # Use small model for routing to save costs/latency
            router_provider = get_provider(model="mistral-small-latest")
            
            router_prompt = self._prompts["chat_router"].format(text=user_message)
            router_response = await router_provider.generate_json_response(router_prompt)
            
            intent = router_response.get("intent", "chat")
            queries = router_response.get("queries", [])
            
            logger.info(f"🧠 Router: intent={intent}, generated {len(queries)} queries")
            
        except Exception as e:
            logger.error(f"Router failed: {e}. Fallback to chat.")
            intent = "chat"
            queries = []

        # 2. Execution Step
        if intent == "rag" and queries:
            try:
                # Multi-Query Retrieval
                all_results = []
                seen_chunks = set()
                
                for q in queries:
                    results = self.vector_store.query(query_text=q, n_results=3)
                    for res in results:
                        # Deduplicate by unique text content
                        if res["text"] not in seen_chunks:
                            seen_chunks.add(res["text"])
                            all_results.append(res)
                
                # Take top 5 chunks
                top_results = sorted(all_results, key=lambda x: x["distance"])[:5]
                
                if not top_results:
                    intent = "chat"
                else:
                    # Enrich context with Abstract of the most relevant paper
                    top_paper_meta = top_results[0].get("metadata", {})
                    top_paper_id = top_paper_meta.get("paper_id")
                    
                    abstract_text = ""
                    if top_paper_id:
                        try:
                            # Fetch abstract from abstracts collection
                            abs_result = self.vector_store.abstracts_collection.get(
                                ids=[top_paper_id],
                                include=["documents"]
                            )
                            if abs_result["documents"]:
                                abstract_doc = abs_result["documents"][0]
                                abstract_text = f"Abstract of {top_paper_meta.get('title', 'Paper')}:\n{abstract_doc}\n\n"
                        except Exception as e:
                            logger.warning(f"Failed to fetch abstract for {top_paper_id}: {e}")

                    # Generate RAG response
                    chunks_text = "\n\n".join([r["text"] for r in top_results])
                    context = f"{abstract_text}Relevant excerpts:\n{chunks_text}"
                    
                    # Collect sources
                    sources = set()
                    for r in top_results:
                        meta = r.get("metadata", {})
                        title = meta.get("title", "Unknown Paper")
                        sources.add(title)
                    
                    sources_list = "\n".join([f"- {s}" for s in sources])
                    
                    rag_prompt = (
                        f"Context from research papers:\n{context}\n\n"
                        f"User Question: {user_message}\n\n"
                        "Answer the question using the context above. "
                        "If the context doesn't contain the answer, say so.\n"
                        f"At the end, list the sources used:\n{sources_list}"
                    )
                    
                    # Use large model for high quality answer
                    generator_provider = get_provider(model="mistral-large-latest")
                    response = await generator_provider.generate_text(rag_prompt)
                    return response
                    
            except Exception as e:
                logger.error(f"RAG failed: {e}. Fallback to chat.")
                # Fallback to chat
        
        # Chat Fallback (or intent="chat")
        chat_provider = get_provider(model="mistral-small-latest")
        return await chat_provider.generate_text(user_message)

