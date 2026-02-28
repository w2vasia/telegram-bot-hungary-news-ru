# Hungary News Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Telegram bot that polls 4 Hungarian RSS feeds every 30 minutes, translates new articles to Russian via DeepL, and posts a ≤500-char summary + source URL to a Telegram channel.

**Architecture:** APScheduler triggers every 30 min → feedparser fetches RSS from 4 sources → SQLite deduplicates by URL → DeepL translates (via abstract Translator interface) → python-telegram-bot posts to channel. Everything runs in Docker with a volume-mounted SQLite file for persistence.

**Tech Stack:** Python 3.12, feedparser, httpx, deepl SDK, python-telegram-bot, APScheduler, SQLite (aiosqlite), pytest, Docker / docker-compose.

---

### Task 1: Project Scaffold

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `bot/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create `.gitignore`**

```
.env
data/
__pycache__/
*.pyc
.pytest_cache/
```

**Step 2: Create `requirements.txt`**

```
feedparser==6.0.11
httpx==0.27.0
deepl==1.18.0
python-telegram-bot==21.5
APScheduler==3.10.4
aiosqlite==0.20.0
pytest==8.3.2
pytest-asyncio==0.23.8
```

**Step 3: Create `.env.example`**

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=@your_channel_id
DEEPL_API_KEY=your_deepl_api_key_here
```

**Step 4: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "bot.main"]
```

**Step 5: Create `docker-compose.yml`**

```yaml
services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./bot:/app/bot
    restart: unless-stopped
```

**Step 6: Create `bot/__init__.py` and `tests/__init__.py`**

Both empty files.

**Step 7: Create `data/.gitkeep`**

Empty file so the data dir is committed but its contents are not.

**Step 8: Verify docker builds**

```bash
cp .env.example .env
docker compose build
```
Expected: build succeeds (will error at runtime without real tokens, that's fine).

**Step 9: Commit**

```bash
git init
git add .
git commit -m "feat: project scaffold with docker"
```

---

### Task 2: Database Layer

**Files:**
- Create: `bot/db.py`
- Create: `tests/test_db.py`

**Step 1: Write failing tests**

```python
# tests/test_db.py
import pytest
import aiosqlite
from bot.db import Database

@pytest.mark.asyncio
async def test_url_not_seen_initially(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.init()
    assert not await db.is_seen("https://example.com/article-1")

@pytest.mark.asyncio
async def test_mark_seen_and_check(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.init()
    url = "https://example.com/article-1"
    await db.mark_seen(url)
    assert await db.is_seen(url)

@pytest.mark.asyncio
async def test_different_urls_independent(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.init()
    await db.mark_seen("https://example.com/a")
    assert not await db.is_seen("https://example.com/b")
```

**Step 2: Run tests to verify they fail**

```bash
docker compose run --rm bot pytest tests/test_db.py -v
```
Expected: ImportError or AttributeError (Database not defined).

**Step 3: Implement `bot/db.py`**

```python
import aiosqlite

class Database:
    def __init__(self, path: str = "data/seen.db"):
        self.path = str(path)

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY)"
            )
            await db.commit()

    async def is_seen(self, url: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT 1 FROM seen_urls WHERE url = ?", (url,)
            ) as cursor:
                return await cursor.fetchone() is not None

    async def mark_seen(self, url: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO seen_urls (url) VALUES (?)", (url,)
            )
            await db.commit()
```

**Step 4: Run tests to verify they pass**

```bash
docker compose run --rm bot pytest tests/test_db.py -v
```
Expected: 3 passed.

**Step 5: Commit**

```bash
git add bot/db.py tests/test_db.py
git commit -m "feat: sqlite db layer for deduplication"
```

---

### Task 3: RSS Feed Fetcher

**Files:**
- Create: `bot/feeds.py`
- Create: `tests/test_feeds.py`

**Step 1: Write failing tests**

```python
# tests/test_feeds.py
import pytest
from bot.feeds import Article, fetch_feed, SOURCES

def test_sources_has_four_entries():
    assert len(SOURCES) == 4

def test_sources_all_have_name_and_url():
    for source in SOURCES:
        assert "name" in source
        assert "url" in source

def test_article_fields():
    a = Article(title="T", url="http://x.com", source="MTI")
    assert a.title == "T"
    assert a.url == "http://x.com"
    assert a.source == "MTI"
```

**Step 2: Run tests to verify they fail**

```bash
docker compose run --rm bot pytest tests/test_feeds.py -v
```
Expected: ImportError.

**Step 3: Implement `bot/feeds.py`**

```python
import feedparser
from dataclasses import dataclass

SOURCES = [
    {"name": "MTI", "url": "https://www.mti.hu/rss/"},
    {"name": "Index", "url": "https://index.hu/24ora/rss/"},
    {"name": "444", "url": "https://444.hu/feed"},
    {"name": "Telex", "url": "https://telex.hu/rss"},
]

@dataclass
class Article:
    title: str
    url: str
    source: str

async def fetch_feed(source: dict) -> list[Article]:
    feed = feedparser.parse(source["url"])
    articles = []
    for entry in feed.entries:
        url = entry.get("link", "")
        title = entry.get("title", "")
        if url and title:
            articles.append(Article(title=title, url=url, source=source["name"]))
    return articles

async def fetch_all() -> list[Article]:
    articles = []
    for source in SOURCES:
        try:
            articles.extend(await fetch_feed(source))
        except Exception as e:
            print(f"[feeds] error fetching {source['name']}: {e}")
    return articles
```

**Step 4: Run tests to verify they pass**

```bash
docker compose run --rm bot pytest tests/test_feeds.py -v
```
Expected: 3 passed.

**Step 5: Commit**

```bash
git add bot/feeds.py tests/test_feeds.py
git commit -m "feat: rss feed fetcher for 4 hungarian sources"
```

---

### Task 4: Translator Interface + DeepL Implementation

**Files:**
- Create: `bot/translator/__init__.py`
- Create: `bot/translator/base.py`
- Create: `bot/translator/deepl.py`
- Create: `tests/test_translator.py`

**Step 1: Write failing tests**

```python
# tests/test_translator.py
import pytest
from bot.translator.base import Translator
from bot.translator.deepl import DeepLTranslator

def test_translator_is_abstract():
    import inspect
    assert inspect.isabstract(Translator)

def test_deepl_translator_implements_interface():
    # DeepLTranslator must be a subclass of Translator
    assert issubclass(DeepLTranslator, Translator)

@pytest.mark.asyncio
async def test_deepl_translate_calls_api(monkeypatch):
    translated_text = "Переведённый текст"

    class FakeResult:
        text = translated_text

    class FakeDeepL:
        def translate_text(self, text, target_lang, source_lang=None):
            return FakeResult()

    translator = DeepLTranslator.__new__(DeepLTranslator)
    translator._client = FakeDeepL()
    result = await translator.translate(
        "Eredeti szöveg", source_lang="HU", target_lang="RU"
    )
    assert result == translated_text
```

**Step 2: Run tests to verify they fail**

```bash
docker compose run --rm bot pytest tests/test_translator.py -v
```
Expected: ImportError.

**Step 3: Create `bot/translator/__init__.py`**

Empty file.

**Step 4: Create `bot/translator/base.py`**

```python
from abc import ABC, abstractmethod

class Translator(ABC):
    @abstractmethod
    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> str:
        """Translate text from source_lang to target_lang."""
```

**Step 5: Create `bot/translator/deepl.py`**

```python
import deepl
from bot.translator.base import Translator

class DeepLTranslator(Translator):
    def __init__(self, api_key: str):
        self._client = deepl.Translator(api_key)

    async def translate(
        self, text: str, source_lang: str = "HU", target_lang: str = "RU"
    ) -> str:
        result = self._client.translate_text(
            text, target_lang=target_lang, source_lang=source_lang
        )
        return result.text
```

**Step 6: Run tests to verify they pass**

```bash
docker compose run --rm bot pytest tests/test_translator.py -v
```
Expected: 3 passed.

**Step 7: Commit**

```bash
git add bot/translator/ tests/test_translator.py
git commit -m "feat: translator interface + deepl implementation"
```

---

### Task 5: Summarizer

**Files:**
- Create: `bot/summarizer.py`
- Create: `tests/test_summarizer.py`

**Step 1: Write failing tests**

```python
# tests/test_summarizer.py
from bot.summarizer import summarize

def test_short_text_unchanged():
    text = "Короткий текст."
    assert summarize(text) == text

def test_long_text_trimmed_to_500():
    text = "А" * 600
    result = summarize(text)
    assert len(result) <= 500

def test_trimmed_ends_with_ellipsis():
    text = "А" * 600
    result = summarize(text)
    assert result.endswith("…")

def test_trim_at_word_boundary():
    # words separated by spaces, trim should not cut mid-word
    text = " ".join(["слово"] * 120)  # well over 500 chars
    result = summarize(text)
    assert not result.rstrip("…").endswith(" ")
    assert "слово" in result
```

**Step 2: Run tests to verify they fail**

```bash
docker compose run --rm bot pytest tests/test_summarizer.py -v
```
Expected: ImportError.

**Step 3: Implement `bot/summarizer.py`**

```python
MAX_CHARS = 500

def summarize(text: str) -> str:
    text = text.strip()
    if len(text) <= MAX_CHARS:
        return text
    truncated = text[:MAX_CHARS - 1]
    last_space = truncated.rfind(" ")
    if last_space > MAX_CHARS // 2:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "…"
```

**Step 4: Run tests to verify they pass**

```bash
docker compose run --rm bot pytest tests/test_summarizer.py -v
```
Expected: 4 passed.

**Step 5: Commit**

```bash
git add bot/summarizer.py tests/test_summarizer.py
git commit -m "feat: summarizer with 500-char limit"
```

---

### Task 6: Telegram Poster

**Files:**
- Create: `bot/poster.py`
- Create: `tests/test_poster.py`

**Step 1: Write failing tests**

```python
# tests/test_poster.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.poster import Poster

@pytest.mark.asyncio
async def test_poster_sends_message():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    poster = Poster(bot=mock_bot, channel_id="@testchannel")
    await poster.post(summary="Тестовая новость", url="https://example.com/news")
    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert "Тестовая новость" in call_kwargs["text"]
    assert "https://example.com/news" in call_kwargs["text"]
    assert call_kwargs["chat_id"] == "@testchannel"

@pytest.mark.asyncio
async def test_poster_uses_html_parse_mode():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    poster = Poster(bot=mock_bot, channel_id="@testchannel")
    await poster.post(summary="Новость", url="https://example.com")
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert call_kwargs.get("parse_mode") == "HTML"
```

**Step 2: Run tests to verify they fail**

```bash
docker compose run --rm bot pytest tests/test_poster.py -v
```
Expected: ImportError.

**Step 3: Implement `bot/poster.py`**

```python
from telegram import Bot

class Poster:
    def __init__(self, bot: Bot, channel_id: str):
        self._bot = bot
        self._channel_id = channel_id

    async def post(self, summary: str, url: str):
        text = f"{summary}\n\n<a href='{url}'>Читать полностью</a>"
        await self._bot.send_message(
            chat_id=self._channel_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )
```

**Step 4: Run tests to verify they pass**

```bash
docker compose run --rm bot pytest tests/test_poster.py -v
```
Expected: 2 passed.

**Step 5: Commit**

```bash
git add bot/poster.py tests/test_poster.py
git commit -m "feat: telegram poster with html formatting"
```

---

### Task 7: Scheduler + Main Entry Point

**Files:**
- Create: `bot/scheduler.py`
- Create: `bot/main.py`

No unit tests for this task (scheduler/main are integration glue; covered by running the bot).

**Step 1: Create `bot/scheduler.py`**

```python
import asyncio
import logging
from bot.db import Database
from bot.feeds import fetch_all
from bot.summarizer import summarize
from bot.translator.deepl import DeepLTranslator
from bot.poster import Poster

logger = logging.getLogger(__name__)

async def run_once(db: Database, translator: DeepLTranslator, poster: Poster):
    articles = await fetch_all()
    for article in articles:
        if await db.is_seen(article.url):
            continue
        try:
            translated = await translator.translate(article.title)
            summary = summarize(translated)
            await poster.post(summary=summary, url=article.url)
            await db.mark_seen(article.url)
            logger.info(f"Posted: {article.url}")
        except Exception as e:
            logger.error(f"Failed to process {article.url}: {e}")
```

**Step 2: Create `bot/main.py`**

```python
import asyncio
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from bot.db import Database
from bot.translator.deepl import DeepLTranslator
from bot.poster import Poster
from bot.scheduler import run_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

async def main():
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]
    deepl_key = os.environ["DEEPL_API_KEY"]

    db = Database()
    await db.init()

    translator = DeepLTranslator(api_key=deepl_key)
    bot = Bot(token=bot_token)
    poster = Poster(bot=bot, channel_id=channel_id)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_once,
        "interval",
        minutes=30,
        args=[db, translator, poster],
    )
    scheduler.start()

    logger.info("Bot started. Polling every 30 minutes.")
    # Run immediately on startup
    await run_once(db, translator, poster)

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

**Step 3: Rebuild and run in Docker**

```bash
docker compose up --build
```
Expected: logs show "Bot started. Polling every 30 minutes." and attempts to fetch feeds.
It will fail to post (no real tokens yet) but should not crash.

**Step 4: Commit**

```bash
git add bot/scheduler.py bot/main.py
git commit -m "feat: scheduler and main entry point"
```

---

### Task 8: Telegram Bot + Channel Setup (manual steps)

**No code changes. Follow these steps:**

**Step 1: Create a Telegram Bot**
1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow prompts — choose a name and username
4. Copy the token BotFather gives you

**Step 2: Create a Telegram Channel**
1. In Telegram: New Channel → set name → Public → choose a username (e.g. `@hungary_news_ru`)
2. Add your bot as administrator to the channel (Manage Channel → Administrators → Add Admin → search your bot)
3. Give it permission to post messages

**Step 3: Get a DeepL API Key**
1. Register at https://www.deepl.com/pro-api (free tier: 500k chars/month)
2. Copy your API key from the account dashboard

**Step 4: Fill in `.env`**

```
TELEGRAM_BOT_TOKEN=<paste bot token>
TELEGRAM_CHANNEL_ID=@hungary_news_ru
DEEPL_API_KEY=<paste deepl key>
```

**Step 5: Start the bot**

```bash
docker compose up --build
```

Watch logs — within seconds you should see the first batch of articles posted to your channel.

---

### Task 9: Run Full Test Suite

**Step 1: Run all tests**

```bash
docker compose run --rm bot pytest tests/ -v
```
Expected: all tests pass.

**Step 2: Commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: test suite passing"
```

---

## Summary

| Task | What it builds |
|------|---------------|
| 1 | Docker scaffold |
| 2 | SQLite deduplication |
| 3 | RSS fetcher (4 sources) |
| 4 | Translator interface + DeepL |
| 5 | 500-char summarizer |
| 6 | Telegram poster |
| 7 | Scheduler + main |
| 8 | Manual bot/channel setup |
| 9 | Full test run |
