# tests/test_scheduler.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import bot.scheduler as scheduler_mod
from bot.scheduler import run_once
from bot.feeds import Article

@pytest.fixture(autouse=True)
def reset_prune_counter():
    scheduler_mod._prune_fail_count = 0

def make_article(url="https://telex.hu/1", title="Teszt cikk", source="Telex"):
    return Article(title=title, url=url, source=source)

def make_deps(articles=None):
    db = MagicMock()
    db.prune = AsyncMock()
    db.is_seen = AsyncMock(return_value=False)
    db.find_similar = AsyncMock(return_value=None)
    db.mark_seen = AsyncMock()

    translator = MagicMock()
    translator.translate = AsyncMock(return_value="Тестовая статья")
    translator.generate = AsyncMock(return_value="политика")

    poster = MagicMock()
    poster.post = AsyncMock()

    if articles is None:
        articles = [make_article()]

    return db, translator, poster, articles

@pytest.mark.asyncio
async def test_skips_already_seen_article():
    db, translator, poster, articles = make_deps()
    db.is_seen = AsyncMock(return_value=True)

    with patch("bot.scheduler.fetch_all", return_value=articles):
        await run_once(db, translator, poster)

    translator.translate.assert_not_called()
    poster.post.assert_not_called()

@pytest.mark.asyncio
async def test_posts_new_article():
    db, translator, poster, articles = make_deps()

    with patch("bot.scheduler.fetch_all", return_value=articles):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await run_once(db, translator, poster)

    poster.post.assert_called_once()
    call_kwargs = poster.post.call_args.kwargs
    assert call_kwargs["url"] == articles[0].url
    assert call_kwargs["source"] == articles[0].source

@pytest.mark.asyncio
async def test_marks_seen_after_posting():
    db, translator, poster, articles = make_deps()

    with patch("bot.scheduler.fetch_all", return_value=articles):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await run_once(db, translator, poster)

    db.mark_seen.assert_called_once_with(articles[0].url, title="Тестовая статья")

@pytest.mark.asyncio
async def test_skips_duplicate_and_marks_seen():
    db, translator, poster, articles = make_deps()
    db.find_similar = AsyncMock(return_value="Похожая статья уже была")

    with patch("bot.scheduler.fetch_all", return_value=articles):
        await run_once(db, translator, poster)

    poster.post.assert_not_called()
    db.mark_seen.assert_called_once_with(articles[0].url, title="Тестовая статья")

@pytest.mark.asyncio
async def test_continues_after_error_on_one_article():
    article1 = make_article(url="https://telex.hu/1", title="Первая")
    article2 = make_article(url="https://telex.hu/2", title="Вторая")
    db, translator, poster, _ = make_deps([article1, article2])
    translator.translate = AsyncMock(side_effect=["Первая статья", "Вторая статья"])
    poster.post = AsyncMock(side_effect=[Exception("Telegram error"), None])

    with patch("bot.scheduler.fetch_all", return_value=[article1, article2]):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await run_once(db, translator, poster)

    assert poster.post.call_count == 2

@pytest.mark.asyncio
async def test_processes_multiple_articles():
    articles = [
        make_article(url="https://telex.hu/1", title="Első"),
        make_article(url="https://telex.hu/2", title="Második"),
        make_article(url="https://telex.hu/3", title="Harmadik"),
    ]
    db, translator, poster, _ = make_deps(articles)
    translator.translate = AsyncMock(side_effect=["Первая", "Вторая", "Третья"])

    with patch("bot.scheduler.fetch_all", return_value=articles):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await run_once(db, translator, poster)

    assert poster.post.call_count == 3
    assert db.mark_seen.call_count == 3

@pytest.mark.asyncio
async def test_skips_batch_duplicate():
    # Same story from two different sources
    article1 = make_article(url="https://telex.hu/1", title="Első")
    article2 = make_article(url="https://hvg.hu/1", title="Második", source="HVG")
    db, translator, poster, _ = make_deps([article1, article2])
    translator.translate = AsyncMock(side_effect=[
        "Венгрия повысила налоги на доходы",
        "Венгрия повысила налоги на доходы граждан",  # very similar (89% match)
    ])

    with patch("bot.scheduler.fetch_all", return_value=[article1, article2]):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await run_once(db, translator, poster)

    # Only first article posted; second skipped as batch duplicate
    assert poster.post.call_count == 1
    # article2 marked seen during Phase 3, article1 marked seen during Phase 4
    assert db.mark_seen.call_count == 2

@pytest.mark.asyncio
async def test_seen_urls_checked_in_parallel():
    """Phase 2 checks all URLs in parallel via asyncio.gather."""
    articles = [
        make_article(url="https://telex.hu/1"),
        make_article(url="https://telex.hu/2"),
    ]
    db, translator, poster, _ = make_deps(articles)
    # First URL already seen, second is new
    db.is_seen = AsyncMock(side_effect=[True, False])
    translator.translate = AsyncMock(return_value="Новая статья")

    with patch("bot.scheduler.fetch_all", return_value=articles):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await run_once(db, translator, poster)

    # Only the new article gets translated and posted
    translator.translate.assert_called_once()
    poster.post.assert_called_once()

@pytest.mark.asyncio
async def test_does_not_mark_seen_when_post_fails():
    db, translator, poster, articles = make_deps()
    poster.post = AsyncMock(side_effect=Exception("Telegram error"))

    with patch("bot.scheduler.fetch_all", return_value=articles):
        await run_once(db, translator, poster)

    db.mark_seen.assert_not_called()

@pytest.mark.asyncio
async def test_aborts_gracefully_on_feed_fetch_failure():
    db, translator, poster, _ = make_deps()
    with patch("bot.scheduler.fetch_all", side_effect=Exception("network error")):
        await run_once(db, translator, poster)
    translator.translate.assert_not_called()
    poster.post.assert_not_called()
