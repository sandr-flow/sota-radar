# Technical Debt

> Items to address post-MVP

---

## TD-001: Sync Database Operations

**Priority:** Medium  
**Impact:** Performance under load  
**Added:** 2026-01-09

**Current state:**  
SQLAlchemy uses synchronous operations with SQLite. DB calls block the event loop.

**Why deferred:**  
For MVP (single user, local SQLite), latency is ~1-10ms — negligible. 

**When to fix:**  
- When migrating to PostgreSQL  
- If bot shows noticeable lag on DB operations  
- When supporting multiple concurrent users

**Solution options:**  
1. Wrap sync calls in `run_in_executor()` (minimal changes)  
2. Migrate to `sqlalchemy.ext.asyncio` (more work, cleaner)

---

## TD-002: Deduplication Query Optimization

**Priority:** Low  
**Impact:** Insert performance  
**Added:** 2026-01-09

**Current state:**  
`exists()` check before each `add()` = 2 queries per paper.

**When to fix:**  
When batch-inserting 1000+ papers and seeing slow performance.

**Solution:**  
Use `INSERT OR IGNORE` or `ON CONFLICT DO NOTHING`.

---

## TD-003: Session Management

**Priority:** Low  
**Impact:** Code quality  
**Added:** 2026-01-09

**Current state:**  
Manual session open/close without context manager.

**Solution:**  
Add `@contextmanager` wrapper for cleaner session handling.

---

## TD-004: LLM API Error Handling & Retries

**Priority:** Medium  
**Impact:** Reliability  
**Added:** 2026-01-09

**Current state:**  
No retry logic on API failures. Single timeout (60s) hardcoded.

**When to fix:**  
When running batch summarization and seeing transient failures.

**Solution:**  
Add exponential backoff retry with `tenacity` or custom implementation.

---

## TD-005: LLM Rate Limiting ✅ RESOLVED

**Priority:** Medium  
**Impact:** API costs, rate limit errors  
**Added:** 2026-01-09  
**Resolved:** 2026-01-09

**Solution implemented:**  
Added `aiolimiter` with 1 RPS limit in `src/llm/rate_limiter.py`.  
All Mistral API calls go through rate limiter in `_call_api()` method.

---

## TD-006: Bot Graceful Shutdown

**Priority:** Low  
**Impact:** Log noise, potential data loss  
**Added:** 2026-01-09

**Current state:**  
`KeyboardInterrupt` causes messy traceback on shutdown. No signal handling.

**Solution:**  
Implement signal handlers for SIGINT/SIGTERM to close sessions and polling cleanly.

---

## TD-007: User Tracking ✅ RESOLVED

**Priority:** Low  
**Impact:** Personalization  
**Added:** 2026-01-09  
**Resolved:** 2026-01-15

**Solution implemented:**  
Added `UserModel` and `UserRepository` in `src/storage/`. Users table tracks `user_id` and `language` preference. Language is captured on /start and stored persistently.

---


## TD-008: Pagination

**Priority:** Low  
**Impact:** UX  
**Added:** 2026-01-09

**Current state:**  
`/digest` shows fixed 10 latest papers. No way to see older ones.

**Solution:**  
Add pagination buttons (InlineKeyboard) to browse older digests.

---

## TD-009: Markdown Support

**Priority:** Low  
**Impact:** UX, content formatting  
**Added:** 2026-01-09

**Current state:**  
Bot uses `parse_mode="HTML"`. LLM summaries might contain Markdown which is currently stripped or displayed raw.

**Solution:**  
Switch to `parse_mode="MarkdownV2"` and ensure LLM output is properly escaped.

---

## TD-010: RAG Retry Logic & Error Handling

**Priority:** Medium  
**Impact:** Reliability  
**Added:** 2026-01-15

**Current state:**  
RAG pipeline has no retry logic for PDF downloads or LLM calls. Single request failure = analysis failure.

**Solution:**  
Add exponential backoff retry with `tenacity` for:
- PDF downloads (network errors, timeouts)
- Mistral API calls (rate limits, 503 errors)

---

## TD-011: RAG Performance Optimization

**Priority:** Medium  
**Impact:** Response time, resource usage  
**Added:** 2026-01-15

**Current state:**  
- Embedding model loads on first request (~5-10s cold start)
- Each question in 3-question format is a separate LLM call (3x latency)
- PDF text extraction not cached

**Solutions:**  
1. Pre-load embedding model on bot startup
2. Batch 3 questions into single LLM call with structured output
3. Cache extracted text in SQLite (`full_text` column in `papers` table)

---

## TD-012: RAG Query Refinement

**Priority:** Low  
**Impact:** Answer quality  
**Added:** 2026-01-15

**Current state:**  
Uses paper title as query for chunk retrieval. May not retrieve most relevant chunks for specific questions.

**Solution:**  
Use question-specific queries for retrieval:
- "essence" → query with "main contribution methodology"  
- "importance" → query with "significance impact problem solving"
- "applications" → query with "applications use cases practical"

---

## TD-013: RAG Quality Metrics

**Priority:** Low  
**Impact:** Observability, quality improvement  
**Added:** 2026-01-15

**Current state:**  
No metrics to evaluate RAG retrieval quality or answer relevance.

**Note:**  
Data flow first, accuracy second. Ensure pipeline is stable before adding metrics.

**Solution:**  
1. Log retrieval distances (ChromaDB similarity scores)
2. Track avg chunks per paper, avg chunk size
3. Add optional user feedback (👍/👎) on analysis quality
4. Consider offline evaluation with ground truth Q&A pairs

---

## TD-014: HuggingFace API Rate Limiting

**Priority:** Low  
**Impact:** Reliability  
**Added:** 2026-01-15

**Current state:**  
HuggingFace Daily Papers API calls are not rate-limited. No retry logic on failures.

**Solution:**  
1. Add rate limiter for HF API calls
2. Implement retry with exponential backoff
3. Consider caching daily papers for 1 hour to reduce API calls

---

## TD-015: Priority Queue Persistence

**Priority:** Low  
**Impact:** Reliability  
**Added:** 2026-01-15

**Current state:**  
Priority summarization queue is in-memory (lost on restart).

**Solution:**  
1. Store queue in SQLite or Redis
2. Add `priority_requested` column to papers table
3. Process papers with `priority_requested=True` first on restart
