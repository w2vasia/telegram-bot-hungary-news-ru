# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
python -m pytest

# Run single test file
python -m pytest tests/test_scheduler.py

# Run single test
python -m pytest tests/test_scheduler.py::test_posts_new_article

# Run bot locally (requires .env with TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID)
python -m bot.main

# Docker
docker compose up --build
```

## Architecture

Telegram bot that polls Hungarian news RSS feeds every 30 min, translates to Russian via Ollama (translategemma model), and posts to `@hungary_news_ru`.

**Pipeline** (`scheduler.run_once`): fetch RSS → filter seen URLs (parallel) → translate each title → cross-source dedup (DB + batch fuzzy matching, 80% threshold) → tag via LLM → summarize (≤500 chars) → post to Telegram.

**Key modules:**
- `bot/feeds.py` — RSS sources list (`SOURCES`) and `Article` dataclass. Sources fetched concurrently via `asyncio.gather`
- `bot/db.py` — SQLite dedup DB (`data/seen.db`). URL uniqueness + fuzzy title matching (rapidfuzz `token_sort_ratio`, 24h window)
- `bot/translator/` — `Translator` ABC in `base.py`. Implementations: `GemmaTranslator` (Ollama HTTP), `DeepLTranslator`, `StubTranslator` (passthrough for tests)
- `bot/tagger.py` — LLM-based tagging from fixed Russian taxonomy (`CATEGORIES` frozenset, max 3 tags). Uses `LLMGenerator` protocol (satisfied by `GemmaTranslator.generate`)
- `bot/poster.py` — Posts HTML-formatted messages to Telegram channel
- `bot/summarizer.py` — Truncates text to 500 chars at word boundary

**Testing patterns:** All async, `asyncio_mode = auto`. Dependencies (db, translator, poster) are mocked with `AsyncMock`. Feed fetching patched via `patch("bot.scheduler.fetch_all")`. Sleep patched to avoid delays.

## Environment

- Python 3.12
- Ollama must be running locally for translation (accessed via `host.docker.internal:11434` in Docker)
- SQLite DB persisted at `data/seen.db` (volume-mounted in Docker)
