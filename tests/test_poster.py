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
