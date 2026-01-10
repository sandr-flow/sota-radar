# sota-radar

> AI-powered Telegram bot for tracking and summarizing latest arXiv papers in Machine Learning and AI

[![Status](https://img.shields.io/badge/status-MVP%20Complete-success)](#features)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**sota-radar** automatically fetches latest research papers from arXiv, generates bilingual summaries using LLM, and delivers personalized digests via Telegram bot with multi-language support.

## Table of Contents

- [Background](#background)
- [Features](#features)
- [Install](#install)
  - [Prerequisites](#prerequisites)
  - [Installation Steps](#installation-steps)
- [Usage](#usage)
  - [Running the Bot](#running-the-bot)
  - [Bot Commands](#bot-commands)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Development](#development)
- [License](#license)

---

## Background

Staying up-to-date with the latest research in AI/ML requires reading dozens of papers daily. **sota-radar** solves this by:

- � **Automated Paper Discovery**: Monitors arXiv categories (cs.LG, cs.CL, cs.CV, cs.AI, cs.NE, cs.IR, stat.ML)
- 🤖 **AI-Powered Summaries**: Uses Mistral LLM to generate concise, bilingual summaries
- 🌐 **Multi-Language Support**: Delivers summaries in English and Russian
- 💬 **Telegram Integration**: User-friendly bot interface with interactive paper selection
- 🔄 **Background Pipeline**: Automatically processes new papers every 5 minutes

## Features

✅ **Core Functionality (MVP Complete)**
- arXiv paper parsing with deduplication
- Bilingual summarization (EN/RU) via Mistral API
- Telegram bot with `/start`, `/digest`, `/language` commands
- User preference storage (language selection)
- Background summarization pipeline with rate limiting (1 RPS)
- SQLite database with SQLAlchemy ORM

✅ **Recent Refactoring (2026-01-10)**
- Centralized configuration with `pydantic-settings`
- Database Engine singleton (fixed connection leaks)
- Shared HTTP client (AsyncClient singleton)
- Externalized prompts (`config/prompts.yaml`)
- Bulk insert optimization with `ON CONFLICT DO NOTHING`

🚧 **Planned Features**
- Retry logic with exponential backoff for API calls
- Pagination for digest browsing
- Docker deployment
- Redis for persistent message tracking

---

## Install

### Prerequisites

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Telegram Account** to create a bot via [BotFather](https://t.me/botfather)
- **Mistral API Key** ([Get free tier key](https://console.mistral.ai/))

### Installation Steps

1. **Clone the repository**

```bash
git clone <your-repo-url>
cd sota-radar
```

2. **Create virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/MacOS
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```ini
# LLM Provider Configuration
MISTRAL_API_KEY=your_mistral_api_key_from_console_mistral_ai

# Telegram Bot Token from @BotFather
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

5. **Initialize database**

The database will be created automatically on first run at `data/sota_radar.db`.

---

## Usage

### Running the Bot

From the project root directory:

```bash
python -m src.bot.main
```

You should see:

```
INFO - Starting sota-radar bot...
INFO - 📡 Background pipeline started (interval: 5min)
```

### Bot Commands

Open Telegram and find your bot by username (set via BotFather):

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and select language (🇬🇧 English / 🇷🇺 Russian) |
| `/language` | Change your preferred language |
| `/digest` | Show latest 10 papers with summaries |
| `/help` | Display available commands |

**Example Workflow:**

1. Send `/start` → Select language (EN/RU)
2. Wait for pipeline to fetch and summarize papers (~5 min)
3. Send `/digest` → See list of papers as buttons
4. Tap a paper title → View full bilingual summary
5. Click links to read full paper on arXiv

---

## Configuration

All configuration is managed via environment variables in `.env`:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MISTRAL_API_KEY` | Mistral AI API key | — | ✅ Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather | — | ✅ Yes |
| `MISTRAL_MODEL` | Mistral model to use | `mistral-large-latest` | No |
| `LLM_PROVIDER` | LLM provider (only `mistral` supported) | `mistral` | No |
| `PIPELINE_INTERVAL_MINUTES` | Minutes between pipeline runs | `5` | No |
| `MAX_RESULTS_PER_CATEGORY` | Max papers to fetch per arXiv category | `100` | No |
| `PAPERS_PER_DIGEST` | Papers shown in `/digest` command | `10` | No |

**Categories Configuration:**

Edit `config/categories.yaml` to customize tracked arXiv categories:

```yaml
categories:
  - id: cs.LG
    name: Machine Learning
  - id: cs.CL
    name: Computation and Language
  # ... add more
```

**Prompts Configuration:**

Customize LLM prompts in `config/prompts.yaml`:

```yaml
prompts:
  bilingual_summary: |
    You are a scientific paper summarization assistant...
```

---

## Project Structure

```
sota-radar/
├── config/                  # Configuration files
│   ├── categories.yaml      # arXiv categories
│   └── prompts.yaml         # LLM prompts
├── data/                    # Database and runtime data
│   └── sota_radar.db        # SQLite database (auto-created)
├── docs/                    # Documentation
│   ├── concept-design.md
│   ├── implementation-plan.md
│   └── tech-debt.md
├── scripts/                 # Utility scripts
│   ├── test_arxiv.py
│   ├── test_llm.py
│   └── run_pipeline.py
├── src/                     # Source code
│   ├── bot/                 # Telegram bot handlers
│   ├── config/              # Settings and config loaders
│   ├── infrastructure/      # Shared HTTP client
│   ├── llm/                 # LLM provider abstractions
│   ├── models/              # Data models
│   ├── pipeline/            # Background summarization
│   ├── sources/             # arXiv parser
│   └── storage/             # Database models and repository
├── tests/                   # Unit tests
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── README.md
```

---

## Documentation

- **[Concept Design](docs/concept-design.md)** — Architecture and design decisions
- **[Technical Debt](docs/tech-debt.md)** — Known issues and future improvements

---

## Development

### Running Tests

```bash
# Run standalone test scripts
python scripts/test_arxiv.py
python scripts/test_llm.py
python scripts/test_storage.py

# Run full pipeline manually
python scripts/run_pipeline.py
```

### Code Quality

The project follows:
- **PEP 257** for docstrings (English)
- **Type hints** throughout codebase
- **SQLAlchemy 2.0** ORM patterns
- **Async/await** for I/O operations

### Architecture Patterns

- **Repository Pattern** for database access
- **Singleton Pattern** for Engine and HTTP client
- **Factory Pattern** for LLM providers
- **Source Adapter Pattern** for extensibility (easy to add new sources beyond arXiv)

---

## License

MIT License - see [LICENSE](LICENSE) file for details.
