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

@pytest.mark.asyncio
async def test_mark_seen_stores_title(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.init()
    await db.mark_seen("https://example.com/a", title="Венгрия повысила налоги")
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        async with conn.execute("SELECT title FROM seen_urls WHERE url = ?", ("https://example.com/a",)) as cur:
            row = await cur.fetchone()
    assert row[0] == "Венгрия повысила налоги"

@pytest.mark.asyncio
async def test_find_similar_matches_near_identical(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.init()
    await db.mark_seen("https://a.com/1", title="Венгрия повысила налоги на доходы граждан")
    result = await db.find_similar("Венгрия повысила налоги на доходы")
    assert result is not None

@pytest.mark.asyncio
async def test_find_similar_no_match_for_unrelated(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.init()
    await db.mark_seen("https://a.com/1", title="Венгрия повысила налоги на доходы")
    result = await db.find_similar("Погода в Будапеште на выходные")
    assert result is None

@pytest.mark.asyncio
async def test_find_similar_respects_time_window(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.init()
    # insert with old timestamp directly
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute(
            "INSERT INTO seen_urls (url, title, posted_at) VALUES (?, ?, datetime('now', '-48 hours'))",
            ("https://a.com/old", "Венгрия повысила налоги на доходы"),
        )
        await conn.commit()
    result = await db.find_similar("Венгрия повысила налоги на доходы", hours=24)
    assert result is None
