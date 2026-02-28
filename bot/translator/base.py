from abc import ABC, abstractmethod


class Translator(ABC):
    @abstractmethod
    async def translate(
        self, text: str, source_lang: str = "HU", target_lang: str = "RU"
    ) -> str:
        """Translate text from source_lang to target_lang."""

    async def close(self) -> None:
        """Release resources. Override in subclasses if needed."""
