import logging
from typing import Protocol
from bot.feeds import Article

logger = logging.getLogger(__name__)

class LLMGenerator(Protocol):
    async def generate(self, prompt: str) -> str: ...

CATEGORIES = frozenset([
    # Politics & Society
    "политика", "выборы", "общество", "право", "безопасность",
    # Economy & Business
    "экономика", "бизнес", "финансы", "рынки", "недвижимость",
    # World
    "мир", "европа", "сша", "украина", "ближнийвосток",
    # Hungary-specific
    "венгрия", "будапешт", "правительство",
    # Life & Culture
    "культура", "спорт", "здоровье", "технологии", "наука",
    "образование", "туризм",
    # Media
    "расследование", "аналитика",
])

MAX_TAGS = 3
_CATEGORIES_STR = ", ".join(sorted(CATEGORIES))

async def get_tags(article: Article, llm: LLMGenerator) -> list[str]:
    try:
        prompt = (
            f"Classify this Hungarian news headline into 1-3 tags. "
            f"Choose ONLY from this exact list: {_CATEGORIES_STR}. "
            f"Return only tag names from the list, space-separated, nothing else. "
            f"Headline: {article.title}"
        )
        result = await llm.generate(prompt)
        words = result.lower().split()
        valid = [f"#{w.strip('.,!?;:')}" for w in words if w.strip('.,!?;:') in CATEGORIES]
        return valid[:MAX_TAGS]
    except Exception as e:
        logger.warning(f"Failed to get tags for {article.url}: {e}")
        return []
