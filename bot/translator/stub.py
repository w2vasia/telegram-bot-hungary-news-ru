from bot.translator.base import Translator


# TODO: replace with real translator (e.g. DeepLTranslator) once API key is available
class StubTranslator(Translator):
    async def translate(self, text: str, source_lang: str = "HU", target_lang: str = "RU") -> str:
        return text

    async def generate(self, prompt: str) -> str:
        return ""
