# sota-radar: Implementation Roadmap

> Granular steps with verifiable outcomes

---

## Phase 0: Project Setup ✅

### 0.1 Repository Structure
- [x] Create folder structure: `src/`, `tests/`, `config/`
- [x] Add `.gitignore` (Python template)
- [x] Add `.env.example` with required variables
- [x] Create `pyproject.toml` or `requirements.txt`

**Verifiable:** `tree` command shows correct structure ✅

### 0.2 Development Environment
- [x] Create virtual environment
- [x] Install base dependencies (httpx, aiogram, python-dotenv)
- [x] Verify imports work

**Verifiable:** `python -c "import aiogram; print('OK')"` succeeds ✅

---

## Phase 1: arXiv Parser ✅

> **Architecture Decision:** Source Adapter Pattern with minimal interface for extensibility

### 1.0 Source Framework ✅
- [x] Create `src/models/paper.py` — unified `Paper` dataclass
- [x] Create `src/sources/base.py` — abstract `BaseSource` with `fetch_papers() -> list[Paper]`

### 1.1 arXiv Client ✅
- [x] Create `src/sources/arxiv.py` implementing `BaseSource`
- [x] Implement `fetch_papers(category, max_results)` function
- [x] Parse XML response to `Paper` dataclass

### 1.2 Category Configuration ✅
- [x] Create `src/config/loader.py` — load categories from `config/categories.yaml`
- [x] Filter by configured categories

### 1.3 Deduplication & Storage ✅
- [x] Create `src/storage/models.py` with Paper SQLAlchemy model
- [x] Create `src/storage/repository.py` with CRUD operations
- [x] Implement "only new papers" logic (skip if `source + source_id` exists)

---

## Phase 2: LLM Gateway ✅

### 2.1 Provider Interface ✅
- [x] Create `src/llm/base.py` with abstract `BaseLLMProvider` class
- [x] Define `summarize(text) -> str` and `translate(text) -> str` methods

### 2.2 Mistral Implementation ✅
- [x] Create `src/llm/mistral.py` implementing `BaseLLMProvider`
- [x] Load API key from env
- [x] Implement summarization with proper prompt

### 2.3 Gateway Factory ✅
- [x] Create `src/llm/gateway.py` with `get_provider(name)` factory
- [x] Support switching providers via env variable

---

## Phase 3: Summarization Pipeline ✅

### 3.1 Background Summarizer ✅
- [x] Create `src/pipeline/summarizer.py`
- [x] Fetch unsummarized papers from DB
- [x] Call LLM gateway, save summary to DB
- [x] Add rate limiting (1 RPS for Mistral free tier via `src/llm/rate_limiter.py`)

### 3.2 Scheduler ✅
- [x] Implemented as background asyncio task in `src/bot/main.py`
- [x] Runs immediately on bot startup
- [x] Repeats every 5 minutes (configurable via `PIPELINE_INTERVAL_MINUTES`)
- [ ] Add manual trigger option (future: `/refresh` command)

**Note:** Using lightweight asyncio approach instead of APScheduler.

---

## Phase 4: Telegram Bot ✅

### 4.1 Bot Skeleton ✅
- [x] Create `src/bot/main.py` with aiogram setup
- [x] Implement `/start` command
- [x] Implement `/help` command

### 4.2 Digest Delivery ✅
- [x] Create `src/bot/handlers.py`
- [x] Implement `/digest` command — show today's papers
- [x] Format message: title + summary + links

### 4.3 Paper Details ✅
- [x] Inline keyboard with paper titles in `/digest`
- [x] Callback handler shows full summary on button click
- [x] Links to arXiv and PDF

### 4.4 Multi-Language Support ✅
- [x] `UserModel` table for language preferences
- [x] `/start` with language selection (🇬🇧/🇷🇺)  
- [x] `/language` command to change preference
- [x] Bilingual summaries stored as JSON `{"en": ..., "ru": ...}`
- [x] Localized UI strings

---

## Phase 5: Summary Translation ✅

> **Decision:** Translation integrated into core pipeline, not a paid feature.

### 5.1 Translator Integration ✅
- [x] Use existing `MistralProvider.translate()` method
- [x] Pipeline generates EN summary, then translates to RU
- [x] Both stored as JSON in `summary_json` field

### 5.2 Payment Integration
- [ ] Deferred — translation now free for all users

---

## Phase 6: Refactoring & Infrastructure ✅

> **Status:** Completed major refactoring to address technical debt

### 6.1 Configuration & Settings ✅
- [x] Centralized configuration using `pydantic-settings`
- [x] Created `src/config/settings.py` with `Settings` class
- [x] Environment variables properly typed and validated
- [x] Removed hardcoded paths and credentials

### 6.2 Database Optimization ✅
- [x] Implemented Singleton pattern for SQLAlchemy Engine
- [x] Fixed connection leak issue in `src/storage/database.py`
- [x] Optimized `PaperRepository.add_many()` with bulk inserts
- [x] Added `ON CONFLICT DO NOTHING` for efficient deduplication

### 6.3 HTTP Client Infrastructure ✅
- [x] Created `src/infrastructure/http_client.py` with singleton `AsyncClient`
- [x] Refactored `MistralProvider` to use shared HTTP client
- [x] Refactored `ArxivSource` to use shared HTTP client
- [x] Added proper `close_client()` on bot shutdown

### 6.4 Prompt Management ✅
- [x] Extracted prompts to `config/prompts.yaml`
- [x] Dynamic prompt loading in `MistralProvider`
- [x] Bilingual summary prompt externalized

### 6.5 Code Quality ✅
- [x] Removed `sys.path` hacks from bot entry point
- [x] Proper module imports throughout project
- [x] Consistent docstring formatting (PEP 257)

---

## Phase 7: RAG Deep Analysis ✅

> **Status:** Completed 2026-01-15

### 7.1 PDF Extraction ✅
- [x] Create `src/rag/pdf_extractor.py` — download and extract text from arXiv PDFs
- [x] Handle redirects and in-memory processing

### 7.2 Semantic Chunking ✅
- [x] Create `src/rag/chunker.py` — split text into meaningful chunks
- [x] Section/paragraph awareness with sentence overlap
- [x] Configurable chunk size (default: 1000 chars)

### 7.3 Vector Store ✅
- [x] Create `src/rag/vector_store.py` — ChromaDB integration
- [x] Persistent storage in `data/chroma/`
- [x] Metadata filtering by paper ID

### 7.4 Embeddings ✅
- [x] Create `src/rag/embeddings.py` — sentence-transformers wrapper
- [x] Model: `all-mpnet-base-v2` (768 dim)
- [x] Lazy loading singleton pattern

### 7.5 RAG Pipeline ✅
- [x] Create `src/rag/rag_pipeline.py` — orchestration
- [x] 3-question format: essence, importance, applications
- [x] "🔬 Deep Analysis" button in Telegram

---

## Phase 8: HuggingFace Trending ✅

> **Status:** Completed 2026-01-15

### 8.1 HuggingFace Source ✅
- [x] Create `src/sources/huggingface.py` — HF Daily Papers adapter
- [x] Fetch trending papers with upvotes
- [x] Filter by arXiv categories

### 8.2 Command Split ✅
- [x] `/digest` — trending from HuggingFace (sorted by upvotes)
- [x] `/latest` — chronological from arXiv DB
- [x] Upvotes displayed in button text (🔥42)

### 8.3 Priority Queue ✅
- [x] Create `src/pipeline/priority_queue.py`
- [x] Papers clicked by users → priority summarization
- [x] Background worker checks queue every 30s
- [x] "Саммари формируется" message for pending papers

---

## Phase 9: Agent Dialog with RAG

> **Status:** Planned

### 9.1 Conversational RAG
- [ ] Multi-turn dialog with paper context
- [ ] User can ask follow-up questions
- [ ] Maintain conversation history per user/paper

### 9.2 Agent Architecture
- [ ] Decide on agent framework (LangChain, custom)
- [ ] Tool calling for chunk retrieval
- [ ] Context window management

### 9.3 Telegram Integration
- [ ] `/chat <paper_id>` command or button
- [ ] Session management (timeout, clear)
- [ ] Handle long conversations gracefully

---

## Phase 10: Configurable Categories

> **Status:** Planned

### 10.1 Per-User Categories
- [ ] Add `categories` column to `UserModel` (JSON array)
- [ ] `/categories` command to view/edit preferences
- [ ] Default: all categories

### 10.2 Filtered Digest
- [ ] `/digest` and `/latest` respect user categories
- [ ] HuggingFace filtering uses user preferences
- [ ] Show category badge in paper list

### 10.3 Onboarding Flow
- [ ] Ask for category preferences on `/start`
- [ ] Inline keyboard with category toggles
- [ ] "Select all" / "Clear" buttons

---

## Phase 11: Background Processing for Old Papers

> **Status:** Planned

### 11.1 RAG Indexing Worker
- [ ] Background task to index papers without embeddings
- [ ] Process N papers per run (configurable)
- [ ] Track `indexed_at` timestamp in DB

### 11.2 Backfill Strategy
- [ ] Priority: papers with most user clicks
- [ ] Secondary: chronological (newest first)
- [ ] Skip papers older than X days (configurable)

### 11.3 Storage Optimization
- [ ] Cache extracted PDF text in DB (`full_text` column)
- [ ] Avoid re-downloading PDFs
- [ ] Prune old ChromaDB entries

---

## Phase 12: Polish & Deploy

> **Status:** Planned

### 12.1 Error Handling
- [ ] Add retry logic for API calls (LLM and arXiv)
- [ ] Implement exponential backoff with `tenacity`
- [ ] Handle edge cases (empty responses, rate limits, timeouts)
- [ ] Add comprehensive logging with log levels

### 12.2 UX Improvements
- [ ] Add pagination for `/digest` command
- [ ] Implement `/refresh` command for manual pipeline trigger
- [ ] Consider Redis for `_summary_messages` persistence
- [ ] Add statistics command (`/stats`)

### 12.3 Deployment
- [ ] Create `Dockerfile` for bot
- [ ] Create `docker-compose.yml` with services
- [ ] Add health check endpoints
- [ ] Deploy to VPS/cloud
- [ ] Set up monitoring and alerting

---

## Decisions Made

| Question | Decision |
|----------|----------|
| arXiv categories | `cs.LG`, `cs.CL`, `cs.CV`, `cs.AI`, `cs.NE`, `cs.IR`, `stat.ML` |
| Papers per digest | 10 (configurable via `PAPERS_PER_DIGEST`) |
| Delivery mode | By command (`/digest`), no auto-schedule for MVP |
| LLM Provider | Mistral (`mistral-large-latest`) |
| Rate limiting | 1 RPS (Mistral free tier, managed via `aiolimiter`) |
| Configuration | `pydantic-settings` with `.env` file |
| Database | SQLite for MVP (easy migration to PostgreSQL) |
| HTTP client | Shared `httpx.AsyncClient` singleton |
| Prompts | Externalized to `config/prompts.yaml` |
| Translation | Free for all users (integrated into pipeline) |
| Trending source | HuggingFace Daily Papers API |
| RAG embeddings | `all-mpnet-base-v2` via sentence-transformers |
| Vector store | ChromaDB (persistent, local) |

---

## Completed Phases Summary

| Phase | Name | Date |
|-------|------|------|
| 0-6 | Core MVP + Refactoring | 2026-01-10 |
| 7 | RAG Deep Analysis | 2026-01-15 |
| 8 | HuggingFace Trending | 2026-01-15 |

**Reference:** See `tech-debt.md` for known issues and future improvements.

