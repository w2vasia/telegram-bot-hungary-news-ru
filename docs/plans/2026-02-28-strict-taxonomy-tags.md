# Strict Taxonomy Tags Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace free-form/RSS-based tagging with a fixed Russian taxonomy of 27 categories — Gemma picks 1-3 from the list per article, hallucinated words are discarded.

**Architecture:** `bot/tagger.py` gets a `CATEGORIES` frozenset and a simplified `get_tags()` that sends article title + the full list to Gemma, splits the response, filters to only known categories, formats as hashtags. `raw_categories` is removed from `Article` and `fetch_feed` since RSS categories are no longer used.

**Tech Stack:** Same as existing — Gemma via Ollama (httpx), feedparser, pytest.

---

### Task 1: Remove `raw_categories` from Article

**Files:**
- Modify: `bot/feeds.py`
- Modify: `tests/test_feeds.py`

**Step 1: Remove the two `raw_categories` tests from `tests/test_feeds.py`**

Delete these two tests:
```python
def test_article_has_raw_categories():
    ...

def test_article_raw_categories_defaults_to_empty():
    ...
```

**Step 2: Run tests to confirm they still pass (now 3 tests):**
```bash
cd /Users/wasiliy/Documents/Projects/telegram-bot-hungary-news-ru && docker compose run --rm bot pytest tests/test_feeds.py -v
```
Expected: 3 passed.

**Step 3: Update `bot/feeds.py` — remove `raw_categories` from Article and fetch_feed**

Replace the entire file with:
```python
import feedparser
from dataclasses import dataclass

SOURCES = [
    {"name": "Telex", "url": "https://telex.hu/rss"},
    {"name": "HVG", "url": "https://hvg.hu/rss"},
    {"name": "24.hu", "url": "https://24.hu/feed/"},
    {"name": "444", "url": "https://444.hu/feed"},
    {"name": "Direkt36", "url": "https://www.direkt36.hu/feed/"},
    {"name": "Átlátszó", "url": "https://atlatszo.hu/feed/"},
    {"name": "Portfolio", "url": "https://www.portfolio.hu/rss/all.xml"},
    {"name": "G7", "url": "https://telex.hu/rss/g7"},
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

**Step 4: Run tests to confirm they still pass:**
```bash
cd /Users/wasiliy/Documents/Projects/telegram-bot-hungary-news-ru && docker compose run --rm bot pytest tests/test_feeds.py -v
```
Expected: 3 passed.

**Step 5: Commit:**
```bash
cd /Users/wasiliy/Documents/Projects/telegram-bot-hungary-news-ru && git add bot/feeds.py tests/test_feeds.py && git commit -m "refactor: remove raw_categories from Article, no longer needed"
```

---

### Task 2: Rewrite tagger with strict taxonomy

**Files:**
- Modify: `bot/tagger.py`
- Modify: `tests/test_tagger.py`

**Step 1: Replace `tests/test_tagger.py` with new tests:**

```python
# tests/test_tagger.py
import pytest
from unittest.mock import AsyncMock
from bot.tagger import get_tags, CATEGORIES
from bot.feeds import Article

def test_categories_is_nonempty_frozenset():
    assert isinstance(CATEGORIES, frozenset)
    assert len(CATEGORIES) > 0

def test_categories_contains_expected_tags():
    assert "политика" in CATEGORIES
    assert "экономика" in CATEGORIES
    assert "спорт" in CATEGORIES
    assert "мир" in CATEGORIES

@pytest.mark.asyncio
async def test_returns_valid_hashtags_from_gemma():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(return_value="политика экономика")
    article = Article(title="Teszt cikk", url="http://x.com", source="HVG")
    tags = await get_tags(article, mock_translator)
    assert tags == ["#политика", "#экономика"]

@pytest.mark.asyncio
async def test_discards_hallucinated_words():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(return_value="политика nonsense выборы фантазия")
    article = Article(title="Teszt", url="http://x.com", source="444")
    tags = await get_tags(article, mock_translator)
    assert "#политика" in tags
    assert "#выборы" in tags
    assert "#nonsense" not in tags
    assert "#фантазия" not in tags

@pytest.mark.asyncio
async def test_max_three_tags():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(return_value="политика экономика спорт культура мир")
    article = Article(title="T", url="http://x.com", source="Telex")
    tags = await get_tags(article, mock_translator)
    assert len(tags) <= 3

@pytest.mark.asyncio
async def test_returns_empty_on_error():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(side_effect=Exception("timeout"))
    article = Article(title="Hír", url="http://x.com", source="Telex")
    tags = await get_tags(article, mock_translator)
    assert tags == []

@pytest.mark.asyncio
async def test_returns_empty_when_no_valid_tags():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(return_value="nonsense garbage invalid")
    article = Article(title="Teszt", url="http://x.com", source="Telex")
    tags = await get_tags(article, mock_translator)
    assert tags == []
```

**Step 2: Run tests to verify they fail:**
```bash
cd /Users/wasiliy/Documents/Projects/telegram-bot-hungary-news-ru && docker compose run --rm bot pytest tests/test_tagger.py -v
```
Expected: failures (CATEGORIES not a frozenset, new test structure doesn't match old impl).

**Step 3: Replace `bot/tagger.py` with new implementation:**

```python
import logging
from bot.feeds import Article
from bot.translator.base import Translator

logger = logging.getLogger(__name__)

CATEGORIES = frozenset([
    # Politics & Society
    "политика", "выборы", "общество", "право", "безопасность",
    # Economy & Business
    "экономика", "бизнес", "финансы", "рынки", "недвижимость",
    # World
    "мир", "европа", "сша", "украина", "ближнийвосток",
    # Hungary-specific
    "венгрия", "будапешт", "правительство",
    # Life & Culture
    "культура", "спорт", "здоровье", "технологии", "наука",
    "образование", "туризм",
    # Media
    "расследование", "аналитика",
])

MAX_TAGS = 3
_CATEGORIES_STR = ", ".join(sorted(CATEGORIES))

async def get_tags(article: Article, translator: Translator) -> list[str]:
    try:
        prompt = (
            f"Classify this Hungarian news headline into 1-3 tags. "
            f"Choose ONLY from this exact list: {_CATEGORIES_STR}. "
            f"Return only tag names from the list, space-separated, nothing else. "
            f"Headline: {article.title}"
        )
        result = await translator.translate(prompt, source_lang="HU", target_lang="RU")
        words = result.lower().split()
        valid = [f"#{w.strip('.,!?;:')}" for w in words if w.strip('.,!?;:') in CATEGORIES]
        return valid[:MAX_TAGS]
    except Exception as e:
        logger.warning(f"Failed to get tags for {article.url}: {e}")
        return []
```

**Step 4: Run tests to verify they all pass:**
```bash
cd /Users/wasiliy/Documents/Projects/telegram-bot-hungary-news-ru && docker compose run --rm bot pytest tests/test_tagger.py -v
```
Expected: 7 passed. Fix if not.

**Step 5: Run full suite to confirm nothing broken:**
```bash
cd /Users/wasiliy/Documents/Projects/telegram-bot-hungary-news-ru && docker compose run --rm bot pytest tests/ -v
```
Expected: all pass.

**Step 6: Commit:**
```bash
cd /Users/wasiliy/Documents/Projects/telegram-bot-hungary-news-ru && git add bot/tagger.py tests/test_tagger.py && git commit -m "feat: strict 27-tag russian taxonomy, discard gemma hallucinations"
```
