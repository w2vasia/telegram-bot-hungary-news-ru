# 🇭🇺 Hungary News Bot

Telegram bot that polls Hungarian news sources every 30 minutes, translates articles to Russian, and posts summaries with source links to a channel.

## Channel

[@hungary_news_ru](https://t.me/hungary_news_ru)

## How it works

1. Fetches RSS feeds from 8 Hungarian news sources
2. Translates article titles to Russian via a local Gemma model (Ollama)
3. Deduplicates via SQLite — each URL is posted only once
4. Cross-source dedup — compares translated titles using fuzzy matching (`rapidfuzz`, 80% threshold, 24h window) so the same story from different outlets is posted only once
5. Tags each article with 1–3 Russian hashtags from a fixed taxonomy via LLM
6. Posts a ≤500-character summary + tags + source link to the Telegram channel

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
- feedparser — RSS fetching
- httpx — HTTP client (Ollama API)
- Ollama (`translategemma:latest`) — local translation + tagging
- deepl — alternative translator (optional)
- python-telegram-bot — posting
- APScheduler — 30-min polling
- aiosqlite — deduplication
- rapidfuzz — cross-source fuzzy title dedup
- Docker / docker-compose

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

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | Channel username, e.g. `@hungary_news_ru` |

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
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        ...
```

Then swap it in `bot/main.py`.
