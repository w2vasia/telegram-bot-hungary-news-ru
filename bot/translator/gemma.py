import httpx
import os
from bot.translator.base import Translator

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://host.docker.internal:11434/api/generate"
)
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "60"))

class GemmaTranslator(Translator):
    def __init__(self, model: str = "translategemma:latest"):
        self._model = model
        self._client = httpx.AsyncClient(timeout=OLLAMA_TIMEOUT)

    async def close(self):
        await self._client.aclose()

    async def generate(self, prompt: str) -> str:
        response = await self._client.post(OLLAMA_URL, json={
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        })
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        if not result:
            raise ValueError("Ollama returned empty response")
        return result

    async def translate(self, text: str, source_lang: str = "HU", target_lang: str = "RU") -> str:
        prompt = (
            f"Translate the following Hungarian text to Russian. "
            f"Return only the translation, no explanations:\n\n{text}"
        )
        return await self.generate(prompt)
