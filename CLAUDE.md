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

**Pipeline** (`scheduler.run_once`): fetch RSS → filter seen URLs (parallel, fault-tolerant) → translate each title → cross-source dedup (DB + batch fuzzy matching, 80% threshold) → mark seen → tag via LLM → summarize (≤500 chars) → post to Telegram.

**Key modules:**
- `bot/feeds.py` — RSS sources list (`SOURCES`) and `Article` dataclass. Sources fetched concurrently via `asyncio.gather`. Socket timeout on feedparser to prevent hangs
- `bot/db.py` — SQLite dedup DB (`data/seen.db`). URL uniqueness + fuzzy title matching (rapidfuzz `token_sort_ratio`, 24h window, LIMIT 5000). All operations protected by `asyncio.Lock`
- `bot/translator/` — `Translator` ABC in `base.py` (with default `close()` and default lang params `HU`/`RU`). Implementations: `GemmaTranslator` (Ollama HTTP, tenacity retry 3x), `DeepLTranslator`, `StubTranslator` (passthrough + `generate()` for tests)
- `bot/tagger.py` — LLM-based tagging from fixed Russian taxonomy (`CATEGORIES` frozenset, max 3 tags). Uses `LLMGenerator` protocol (satisfied by `GemmaTranslator.generate` and `StubTranslator.generate`)
- `bot/poster.py` — Posts HTML-formatted messages to Telegram channel. Handles `RetryAfter` (429) with sleep+retry
- `bot/summarizer.py` — Truncates text to 500 chars at word boundary. None-safe
- `bot/main.py` — Entry point. Loads dotenv, runs health checks (Ollama + Telegram), first `run_once` with timeout, then starts scheduler. Graceful shutdown (`wait=True`)

**Reliability patterns:**
- Mark-before-post: articles marked seen before posting to prevent duplicate posts on failure
- Phase 2 uses `return_exceptions=True` — individual `is_seen` failures don't kill the cycle
- Prune failure counter escalates to `raise` after 10 consecutive failures
- All DB writes/reads protected by asyncio.Lock
- Configurable delays via env vars (`POST_DELAY`, `STARTUP_TIMEOUT`, `OLLAMA_TIMEOUT`)

**Testing patterns:** All async, `asyncio_mode = auto`. Dependencies (db, translator, poster) are mocked with `AsyncMock`. Feed fetching patched via `patch("bot.scheduler.fetch_all")`. Sleep patched to avoid delays. `reset_prune_counter` autouse fixture resets global state. GemmaTranslator tested with mock httpx client (retry, JSON errors, lang params).

## Environment

- Python 3.12
- `python-dotenv` loads `.env` automatically (optional dep, graceful fallback)
- Ollama must be running locally for translation (accessed via `host.docker.internal:11434` in Docker, configurable via `OLLAMA_URL`)
- SQLite DB persisted at `data/seen.db` (volume-mounted in Docker)
- See `.env.example` for all configurable env vars
