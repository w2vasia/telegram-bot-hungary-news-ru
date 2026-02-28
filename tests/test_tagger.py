# tests/test_tagger.py
from unittest.mock import AsyncMock

import pytest

from bot.tagger import CATEGORIES, get_tags


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
    tags = await get_tags("Тестовая новость", mock_translator)
    assert tags == ["#политика", "#экономика"]

@pytest.mark.asyncio
async def test_discards_hallucinated_words():
    mock_translator = AsyncMock()
    mock_translator.generate = AsyncMock(return_value="политика nonsense выборы фантазия")
    tags = await get_tags("Тестовый заголовок", mock_translator)
    assert "#политика" in tags
    assert "#выборы" in tags
    assert "#nonsense" not in tags
    assert "#фантазия" not in tags

@pytest.mark.asyncio
async def test_max_three_tags():
    mock_translator = AsyncMock()
    mock_translator.generate = AsyncMock(return_value="политика экономика спорт культура мир")
    tags = await get_tags("Заголовок", mock_translator)
    assert len(tags) == 3

@pytest.mark.asyncio
async def test_returns_empty_on_error():
    mock_translator = AsyncMock()
    mock_translator.generate = AsyncMock(side_effect=Exception("timeout"))
    tags = await get_tags("Заголовок", mock_translator)
    assert tags == []

@pytest.mark.asyncio
async def test_returns_empty_when_no_valid_tags():
    mock_translator = AsyncMock()
    mock_translator.generate = AsyncMock(return_value="nonsense garbage invalid")
    tags = await get_tags("Заголовок", mock_translator)
    assert tags == []
