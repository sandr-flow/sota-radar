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

## Phase 5: Translation ✅

> **Decision:** Translation integrated into core pipeline, not a paid feature.

### 5.1 Translator Integration ✅
- [x] Use existing `MistralProvider.translate()` method
- [x] Pipeline generates EN summary, then translates to RU
- [x] Both stored as JSON in `summary_json` field

### 5.2 Payment Integration
- [ ] Deferred — translation now free for all users

---

## Phase 6: Polish & Deploy

### 6.1 Error Handling
- [ ] Add retry logic for API calls
- [ ] Add proper logging
- [ ] Handle edge cases (empty responses, rate limits)

### 6.2 Deployment
- [ ] Create `Dockerfile`
- [ ] Create `docker-compose.yml`
- [ ] Deploy to VPS/cloud

---

## Decisions Made

| Question | Decision |
|----------|----------|
| arXiv categories | `cs.LG`, `cs.CL`, `cs.CV`, `cs.AI`, `cs.NE`, `cs.IR`, `stat.ML` |
| Papers per digest | 10 |
| Delivery mode | By command (`/digest`), no auto-schedule for MVP |
| LLM Model | `mistral-large-latest` |
| Rate limiting | 1 RPS (Mistral free tier) |
| Payment provider | TBD (Phase 5) |
