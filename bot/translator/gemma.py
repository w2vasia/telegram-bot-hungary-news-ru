import json
import httpx
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from bot.translator.base import Translator

OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://host.docker.internal:11434/api/generate"
)
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "60"))

_RETRY_EXCEPTIONS = (httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError)

class GemmaTranslator(Translator):
    def __init__(self, model: str = "translategemma:latest"):
        self._model = model
        self._client = httpx.AsyncClient(timeout=OLLAMA_TIMEOUT)

    async def close(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
    )
    async def generate(self, prompt: str) -> str:
        response = await self._client.post(OLLAMA_URL, json={
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        })
        response.raise_for_status()
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Ollama returned invalid JSON: {e}") from e
        result = data.get("response", "").strip()
        if not result:
            raise ValueError("Ollama returned empty response")
        return result

    async def translate(self, text: str, source_lang: str = "HU", target_lang: str = "RU") -> str:
        prompt = (
            f"Translate the following {source_lang} text to {target_lang}. "
            f"Return only the translation, no explanations:\n\n{text}"
        )
        return await self.generate(prompt)
