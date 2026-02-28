# tests/test_translator.py
import pytest

from bot.translator.base import Translator
from bot.translator.deepl import DeepLTranslator


def test_translator_is_abstract():
    import inspect
    assert inspect.isabstract(Translator)

def test_deepl_translator_implements_interface():
    assert issubclass(DeepLTranslator, Translator)

@pytest.mark.asyncio
async def test_deepl_translate_calls_api(monkeypatch):
    translated_text = "Переведённый текст"

    class FakeResult:
        text = translated_text

    class FakeDeepL:
        def translate_text(self, text, target_lang, source_lang=None):
            return FakeResult()

    translator = DeepLTranslator.__new__(DeepLTranslator)
    translator._client = FakeDeepL()
    result = await translator.translate(
        "Eredeti szöveg", source_lang="HU", target_lang="RU"
    )
    assert result == translated_text
