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
