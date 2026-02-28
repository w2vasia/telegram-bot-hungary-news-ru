import deepl
from bot.translator.base import Translator

class DeepLTranslator(Translator):
    def __init__(self, api_key: str):
        self._client = deepl.Translator(api_key)

    async def translate(
        self, text: str, source_lang: str = "HU", target_lang: str = "RU"
    ) -> str:
        result = self._client.translate_text(
            text, target_lang=target_lang, source_lang=source_lang
        )
        return result.text
