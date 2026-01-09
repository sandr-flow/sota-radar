# arXiv Parser & Translator

> **Status:** Draft / Concept  
> **Created:** 2026-01-09

## Overview

AI-powered research aggregator that parses scientific papers from arXiv, summarizes them using LLM, and delivers personalized digests to users via Telegram bot. Includes paid translation feature.

---

## Core Features

### MVP (Phase 1)

| Feature | Description |
|---------|-------------|
| **arXiv Parser** | Fetch new papers from arXiv API by categories/keywords |
| **AI Summarization** | Background summarization via provider-agnostic LLM gateway (Mistral for dev) |
| **Telegram Bot** | Deliver digests on schedule or by trigger (aiogram) |
| **Read Summary** | View AI-generated summary in bot |
| **Original Access** | Link to arXiv page + PDF download |
| **Translation** | AI-powered translation (paid feature) |

### Future Considerations

- [ ] Additional sources (Hugging Face Papers, Papers With Code, AI company blogs)
- [ ] Advanced filtering (by authors, organizations, citation count)
- [ ] Reading history & bookmarks
- [ ] Extended monetization options

---

## Architecture (High-Level)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ arXiv API   │────▶│   Parser     │────▶│  Database   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                    ┌──────────────┐            │
                    │ LLM Gateway  │◀───────────┤
                    │  (Mistral)   │            │
                    └──────┬───────┘            │
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │  Summarizer  │────▶│   Telegram  │
                    │  Translator  │     │     Bot     │
                    └──────────────┘     └─────────────┘
```

---

## Technical Stack (Proposed)

| Component | Technology | Notes |
|-----------|------------|-------|
| Language | Python | Best fit for ML ecosystem + aiogram |
| Bot Framework | aiogram 3.x | Async Telegram bot |
| LLM Gateway | Custom (provider-agnostic) | Mistral API for development |
| Parser | arxiv Python library / direct API | RSS + REST API |
| Database | SQLite → PostgreSQL | Start simple, migrate for scale |
| Task Queue | — | TBD (Celery/APScheduler for background jobs) |
| Translator | Port from TypeScript prototype | Adapt from fiction to scientific style |

---

## Design Principles

1. **Start simple, design for scale** — Personal use first, but architecture supports multiple users
2. **Provider-agnostic AI** — Easy switch between LLM providers (Mistral → OpenAI → Claude → local)
3. **Modular components** — Parser, summarizer, translator, bot as separate modules
4. **Async-first** — Non-blocking operations for better performance

---

## Cost Model

| Operation | Frequency | Cost Strategy |
|-----------|-----------|---------------|
| **Summarization** | Once per paper | Cached in DB, shared across all users |
| **Translation** | Per user request | Paid feature (personalized, on-demand) |

**Key insight:** Summaries are generated **once** and stored. All users receive the same cached summary — cost scales with paper count, not user count.

```
Paper → Summarize (1x) → Cache → Serve to N users (free)
                                      ↓
                              User requests translation → Paid API call
```

Estimated summarization cost: ~$1-2/day for 100 papers (assuming ~$0.01-0.02 per summary with Mistral).

---

## Open Questions

- [ ] Exact arXiv categories to track
- [ ] Filtering logic (keywords, authors, popularity)
- [ ] Digest format and frequency
- [ ] Translation pricing model
- [ ] Storage requirements (full papers vs. metadata only)

---

## References

- [arXiv API](https://arxiv.org/help/api)
- [aiogram Documentation](https://docs.aiogram.dev/)
- [Mistral API](https://docs.mistral.ai/)
- TypeScript translator prototype (to be adapted)
