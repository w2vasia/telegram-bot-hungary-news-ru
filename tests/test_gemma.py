# tests/test_gemma.py
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bot.translator.gemma import GemmaTranslator


@pytest.fixture
def translator():
    t = GemmaTranslator(model="test-model")
    yield t


def _mock_response(data=None, status=200, text=""):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    if data is not None:
        resp.json.return_value = data
    else:
        resp.json.side_effect = json.JSONDecodeError("bad", "", 0)
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


@pytest.mark.asyncio
async def test_generate_success(translator):
    translator._client.post = AsyncMock(
        return_value=_mock_response({"response": "result text"})
    )
    result = await translator.generate("test prompt")
    assert result == "result text"


@pytest.mark.asyncio
async def test_generate_empty_response_raises(translator):
    translator._client.post = AsyncMock(
        return_value=_mock_response({"response": ""})
    )
    with pytest.raises(ValueError, match="empty response"):
        await translator.generate("test")


@pytest.mark.asyncio
async def test_generate_invalid_json_raises(translator):
    translator._client.post = AsyncMock(
        return_value=_mock_response()  # json() raises JSONDecodeError
    )
    with pytest.raises(ValueError, match="invalid JSON"):
        await translator.generate("test")


@pytest.mark.asyncio
async def test_generate_retries_on_connect_error(translator):
    translator._client.post = AsyncMock(side_effect=[
        httpx.ConnectError("refused"),
        _mock_response({"response": "ok"}),
    ])
    result = await translator.generate("test")
    assert result == "ok"
    assert translator._client.post.call_count == 2


@pytest.mark.asyncio
async def test_generate_gives_up_after_3_retries(translator):
    from tenacity import RetryError
    translator._client.post = AsyncMock(
        side_effect=httpx.ConnectError("refused")
    )
    with pytest.raises(RetryError):
        await translator.generate("test")
    assert translator._client.post.call_count == 3


@pytest.mark.asyncio
async def test_translate_uses_lang_params(translator):
    translator._client.post = AsyncMock(
        return_value=_mock_response({"response": "translated"})
    )
    result = await translator.translate("hello", source_lang="EN", target_lang="DE")
    assert result == "translated"
    call_json = translator._client.post.call_args[1]["json"]
    assert "EN" in call_json["prompt"]
    assert "DE" in call_json["prompt"]


@pytest.mark.asyncio
async def test_translate_default_langs(translator):
    translator._client.post = AsyncMock(
        return_value=_mock_response({"response": "перевод"})
    )
    await translator.translate("szöveg")
    call_json = translator._client.post.call_args[1]["json"]
    assert "HU" in call_json["prompt"]
    assert "RU" in call_json["prompt"]


@pytest.mark.asyncio
async def test_close(translator):
    translator._client = AsyncMock()
    await translator.close()
    translator._client.aclose.assert_awaited_once()
