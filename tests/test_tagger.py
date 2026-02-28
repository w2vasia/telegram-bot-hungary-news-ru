# tests/test_tagger.py
import pytest
from unittest.mock import AsyncMock
from bot.tagger import get_tags, CATEGORIES
from bot.feeds import Article

def test_categories_is_nonempty_frozenset():
    assert isinstance(CATEGORIES, frozenset)
    assert len(CATEGORIES) == 27

def test_categories_contains_expected_tags():
    assert "политика" in CATEGORIES
    assert "экономика" in CATEGORIES
    assert "спорт" in CATEGORIES
    assert "мир" in CATEGORIES

@pytest.mark.asyncio
async def test_returns_valid_hashtags_from_gemma():
    mock_translator = AsyncMock()
    mock_translator.generate = AsyncMock(return_value="политика экономика")
    article = Article(title="Teszt cikk", url="http://x.com", source="HVG")
    tags = await get_tags(article, mock_translator)
    assert tags == ["#политика", "#экономика"]

@pytest.mark.asyncio
async def test_discards_hallucinated_words():
    mock_translator = AsyncMock()
    mock_translator.generate = AsyncMock(return_value="политика nonsense выборы фантазия")
    article = Article(title="Teszt", url="http://x.com", source="444")
    tags = await get_tags(article, mock_translator)
    assert "#политика" in tags
    assert "#выборы" in tags
    assert "#nonsense" not in tags
    assert "#фантазия" not in tags

@pytest.mark.asyncio
async def test_max_three_tags():
    mock_translator = AsyncMock()
    mock_translator.generate = AsyncMock(return_value="политика экономика спорт культура мир")
    article = Article(title="T", url="http://x.com", source="Telex")
    tags = await get_tags(article, mock_translator)
    assert len(tags) == 3

@pytest.mark.asyncio
async def test_returns_empty_on_error():
    mock_translator = AsyncMock()
    mock_translator.generate = AsyncMock(side_effect=Exception("timeout"))
    article = Article(title="Hír", url="http://x.com", source="Telex")
    tags = await get_tags(article, mock_translator)
    assert tags == []

@pytest.mark.asyncio
async def test_returns_empty_when_no_valid_tags():
    mock_translator = AsyncMock()
    mock_translator.generate = AsyncMock(return_value="nonsense garbage invalid")
    article = Article(title="Teszt", url="http://x.com", source="Telex")
    tags = await get_tags(article, mock_translator)
    assert tags == []
