# tests/test_poster.py
from unittest.mock import AsyncMock, MagicMock

import pytest

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
    assert 'href="https://example.com/news"' in call_kwargs["text"]
    assert call_kwargs["chat_id"] == "@testchannel"

@pytest.mark.asyncio
async def test_poster_uses_html_parse_mode():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    poster = Poster(bot=mock_bot, channel_id="@testchannel")
    await poster.post(summary="Новость", url="https://example.com")
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert call_kwargs.get("parse_mode") == "HTML"

@pytest.mark.asyncio
async def test_poster_includes_tags_between_summary_and_link():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    poster = Poster(bot=mock_bot, channel_id="@testchannel")
    await poster.post(summary="Новость", url="https://example.com",
                      tags=["#политика", "#экономика"])
    text = mock_bot.send_message.call_args.kwargs["text"]
    summary_pos = text.index("Новость")
    tags_pos = text.index("#политика")
    link_pos = text.index('href="https://example.com"')
    assert summary_pos < tags_pos < link_pos

@pytest.mark.asyncio
async def test_poster_no_tags_line_when_empty():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    poster = Poster(bot=mock_bot, channel_id="@testchannel")
    await poster.post(summary="Новость", url="https://example.com", tags=[])
    text = mock_bot.send_message.call_args.kwargs["text"]
    expected = 'Новость\n\n<a href="https://example.com">Источник</a>'
    assert text == expected

@pytest.mark.asyncio
async def test_poster_uses_source_name_as_link_title():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    poster = Poster(bot=mock_bot, channel_id="@testchannel")
    await poster.post(summary="Новость", url="https://index.hu/article", source="Index.hu")
    text = mock_bot.send_message.call_args.kwargs["text"]
    assert '<a href="https://index.hu/article">Index.hu</a>' in text

@pytest.mark.asyncio
async def test_poster_escapes_html_in_summary_and_source():
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    poster = Poster(bot=mock_bot, channel_id="@testchannel")
    await poster.post(
        summary='Title with <b>HTML</b> & "quotes"',
        url="https://example.com/a?b=1&c=2",
        source="A&B",
    )
    text = mock_bot.send_message.call_args.kwargs["text"]
    assert "&lt;b&gt;" in text
    assert "&amp;B" in text
    assert 'href="https://example.com/a?b=1&amp;c=2"' in text
