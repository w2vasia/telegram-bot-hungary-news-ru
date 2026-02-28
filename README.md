# 🇭🇺 Hungary News Bot

Telegram bot that polls Hungarian news sources every 30 minutes, translates articles to Russian, and posts summaries with source links to a channel.

## Channel

[@hungary_news_ru](https://t.me/hungary_news_ru)

## How it works

1. Fetches RSS feeds from 4 Hungarian news sources (MTI, Index, 444, Telex)
2. Translates article titles to Russian via a local Gemma model (Ollama)
3. Posts a ≤500-character summary + link to the Telegram channel
4. Deduplicates via SQLite — each URL is posted only once
5. Cross-source dedup — compares translated titles using fuzzy matching (`rapidfuzz`, 80% threshold, 24h window) so the same story from different outlets is posted only once

## Sources

| Source | URL |
|--------|-----|
| MTI | https://www.mti.hu |
| Index | https://index.hu |
| 444 | https://444.hu |
| Telex | https://telex.hu |

## Stack

- Python 3.12
- feedparser — RSS fetching
- Ollama (`translategemma:latest`) — local translation
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
├── scheduler.py     # run_once: fetch → translate → post
├── feeds.py         # RSS fetcher (4 sources)
├── summarizer.py    # ≤500-char trimmer
├── poster.py        # Telegram HTML post
├── db.py            # SQLite dedup (URL + fuzzy title matching)
└── translator/
    ├── base.py      # abstract Translator interface
    ├── gemma.py     # Ollama/Gemma implementation
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
