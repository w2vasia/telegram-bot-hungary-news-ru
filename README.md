# 🇭🇺 Hungary News Bot

Telegram bot that polls Hungarian news sources every 30 minutes, translates articles to Russian, and posts summaries with source links to a channel.

## Channel

[@hungary_news_ru](https://t.me/hungary_news_ru)

## How it works

1. Fetches RSS feeds from 8 Hungarian news sources (concurrent, with socket timeouts)
2. Filters already-seen URLs in parallel (fault-tolerant — individual failures don't kill the cycle)
3. Translates article titles to Russian via a local Gemma model (Ollama, with retry on failure)
4. Cross-source dedup — compares translated titles using fuzzy matching (`rapidfuzz`, 80% threshold, 24h window) so the same story from different outlets is posted only once
5. Tags each article with 1–3 Russian hashtags from a fixed taxonomy via LLM
6. Marks article as seen, then posts a ≤500-character summary + tags + source link to the Telegram channel (handles Telegram 429 rate limits)

## Sources

| Source | URL |
|--------|-----|
| Telex | https://telex.hu |
| HVG | https://hvg.hu |
| 24.hu | https://24.hu |
| 444 | https://444.hu |
| Direkt36 | https://www.direkt36.hu |
| Átlátszó | https://atlatszo.hu |
| Portfolio | https://www.portfolio.hu |
| G7 | https://telex.hu/g7 |

## Stack

- Python 3.12
- feedparser — RSS fetching (with socket timeouts)
- httpx — HTTP client (Ollama API)
- Ollama (`translategemma:latest`) — local translation + tagging
- tenacity — retry with exponential backoff on Ollama calls
- deepl — alternative translator (optional)
- python-telegram-bot — posting (with 429 retry handling)
- python-dotenv — `.env` file loading for local dev
- APScheduler — 30-min polling
- aiosqlite — deduplication (with asyncio.Lock)
- rapidfuzz — cross-source fuzzy title dedup
- Docker / docker-compose (resource limits, healthcheck)

## Setup

### Prerequisites

- Docker + docker-compose
- [Ollama](https://ollama.com) running locally with `translategemma` pulled:
  ```bash
  ollama pull translategemma
  ```
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A public Telegram channel with your bot added as admin

### Run

```bash
cp .env.example .env
# fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID
docker compose up --build
```

### Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | yes | — | Bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | yes | — | Channel username, e.g. `@hungary_news_ru` |
| `OLLAMA_URL` | no | `http://host.docker.internal:11434/api/generate` | Ollama API endpoint |
| `OLLAMA_TIMEOUT` | no | `60` | Ollama request timeout (seconds) |
| `POST_DELAY` | no | `3` | Delay between Telegram posts (seconds) |
| `STARTUP_TIMEOUT` | no | `300` | Max time for initial run_once (seconds) |

## Project structure

```
bot/
├── main.py          # entry point
├── scheduler.py     # run_once: fetch → translate → dedup → tag → post
├── feeds.py         # RSS fetcher (8 sources)
├── tagger.py        # LLM-based tagging (fixed Russian taxonomy, max 3 tags)
├── summarizer.py    # ≤500-char trimmer
├── poster.py        # Telegram HTML post
├── db.py            # SQLite dedup (URL + fuzzy title matching)
└── translator/
    ├── base.py      # abstract Translator interface
    ├── gemma.py     # Ollama/Gemma implementation
    ├── deepl.py     # DeepL API implementation
    └── stub.py      # passthrough stub (for testing)
```

## Adding a new translator

Implement the `Translator` interface in `bot/translator/`:

```python
from bot.translator.base import Translator

class MyTranslator(Translator):
    async def translate(self, text: str, source_lang: str = "HU", target_lang: str = "RU") -> str:
        ...

    # Optional: implement generate() to support LLM tagging
    async def generate(self, prompt: str) -> str:
        ...
```

Then swap it in `bot/main.py`.
