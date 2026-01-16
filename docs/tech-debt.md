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

## TD-002: Deduplication Query Optimization ✅ RESOLVED

---

## TD-003: Session Management ✅ RESOLVED

---

## TD-004: LLM API Error Handling & Retries

**Priority:** Medium  
**Impact:** Reliability  
**Added:** 2026-01-09

**Current state:**  
No retry logic on LLM API failures.

**Solution:**  
Add exponential backoff retry for Mistral API calls.

---

## TD-005: LLM Rate Limiting ✅ RESOLVED

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

## TD-010: RAG Retry Logic & Error Handling ✅ PARTIALLY RESOLVED

**Added:** 2026-01-15  
**Partial:** 2026-01-16

PDF downloads now have retry with exponential backoff.  
**Remaining:** Mistral API calls in RAG pipeline still need retry logic.

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
Use question-specific queries for retrieval.

---

## TD-013: RAG Quality Metrics

**Priority:** Low  
**Impact:** Observability, quality improvement  
**Added:** 2026-01-15

**Current state:**  
No metrics to evaluate RAG retrieval quality or answer relevance.

**Solution:**  
1. Log retrieval distances (ChromaDB similarity scores)
2. Track avg chunks per paper, avg chunk size
3. Add optional user feedback (👍/👎) on analysis quality

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

## TD-015: Priority Queue Persistence ✅ RESOLVED

---

## TD-016: Разделение MistralProvider (SRP)

**Priority:** Low  
**Impact:** Testability, maintainability  
**Added:** 2026-01-16

**Current state:**  
Класс совмещает HTTP-логику, rate limiting и бизнес-логику суммаризации.

**Solution:**  
Разделить на `MistralApiClient` и `MistralProvider`.

**When to fix:**  
При добавлении юнит-тестов или переходе на другой LLM provider.

---

## TD-017: Dependency Injection для глобальных объектов

**Priority:** Low  
**Impact:** Testability  
**Added:** 2026-01-16

**Current state:**  
Глобальные `MISTRAL_RATE_LIMITER` и `_client` затрудняют тестирование.

**Solution:**  
Убрать глобальные объекты, передавать зависимости через DI или фабрики.

**When to fix:**  
При добавлении юнит-тестов или переходе на multi-instance deployment.

---

## TD-018: Рефакторинг RAGPipeline

**Priority:** Medium  
**Impact:** Code maintainability  
**Added:** 2026-01-16

**Current state:**  
God-object на 200+ строк с PDF загрузкой, чанкингом, эмбеддингами и генерацией ответов.

**Solution:**  
Разделить на `PaperIndexer`, `PaperRetriever`, `AnswerGenerator`.

**When to fix:**  
При существенном расширении RAG-функционала.
