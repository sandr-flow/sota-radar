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

## TD-007: User Tracking

**Priority:** Low  
**Impact:** Personalization  
**Added:** 2026-01-09

**Current state:**  
Bot is stateless regarding users. Doesn't track who is using it.

**When to fix:**  
When complying with Phase 5 (paid translations) or multi-user preferences.

**Solution:**  
Add `users` table to DB. Capture `user_id` on /start.

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
