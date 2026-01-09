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
