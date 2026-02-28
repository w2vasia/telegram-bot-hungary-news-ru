# tests/test_tagger.py
import pytest
from unittest.mock import AsyncMock
from bot.tagger import get_tags
from bot.feeds import Article

@pytest.mark.asyncio
async def test_uses_rss_categories_when_available():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(return_value="политика экономика")
    article = Article(title="Teszt", url="http://x.com", source="HVG",
                      raw_categories=["belfold", "gazdasag"])
    tags = await get_tags(article, mock_translator)
    assert tags == ["#политика", "#экономика"]
    mock_translator.translate.assert_called_once()

@pytest.mark.asyncio
async def test_falls_back_to_classification_when_no_categories():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(return_value="политика")
    article = Article(title="Valami hír", url="http://x.com", source="444",
                      raw_categories=[])
    tags = await get_tags(article, mock_translator)
    assert tags == ["#политика"]
    mock_translator.translate.assert_called_once()

@pytest.mark.asyncio
async def test_returns_empty_on_translator_error():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(side_effect=Exception("timeout"))
    article = Article(title="Hír", url="http://x.com", source="Telex",
                      raw_categories=[])
    tags = await get_tags(article, mock_translator)
    assert tags == []

@pytest.mark.asyncio
async def test_max_three_tags():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(return_value="политика экономика спорт культура")
    article = Article(title="T", url="http://x.com", source="HVG",
                      raw_categories=["a", "b", "c", "d"])
    tags = await get_tags(article, mock_translator)
    assert len(tags) <= 3

@pytest.mark.asyncio
async def test_tags_are_lowercase_hashtags():
    mock_translator = AsyncMock()
    mock_translator.translate = AsyncMock(return_value="Политика")
    article = Article(title="T", url="http://x.com", source="HVG",
                      raw_categories=["belfold"])
    tags = await get_tags(article, mock_translator)
    assert all(t.startswith("#") for t in tags)
    assert all(t == t.lower() for t in tags)
