import httpx
from bot.translator.base import Translator

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"

class GemmaTranslator(Translator):
    def __init__(self, model: str = "translategemma:latest"):
        self._model = model

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(OLLAMA_URL, json={
                "model": self._model,
                "prompt": prompt,
                "stream": False,
            })
            response.raise_for_status()
            return response.json()["response"].strip()

    async def translate(self, text: str, source_lang: str = "HU", target_lang: str = "RU") -> str:
        prompt = (
            f"Translate the following Hungarian text to Russian. "
            f"Return only the translation, no explanations:\n\n{text}"
        )
        return await self.generate(prompt)
