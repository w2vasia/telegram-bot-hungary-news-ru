import logging
from bot.feeds import Article
from bot.translator.base import Translator

logger = logging.getLogger(__name__)

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

async def get_tags(article: Article, translator: Translator) -> list[str]:
    try:
        prompt = (
            f"Classify this Hungarian news headline into 1-3 tags. "
            f"Choose ONLY from this exact list: {_CATEGORIES_STR}. "
            f"Return only tag names from the list, space-separated, nothing else. "
            f"Headline: {article.title}"
        )
        result = await translator.translate(prompt, source_lang="HU", target_lang="RU")
        words = result.lower().split()
        valid = [f"#{w.strip('.,!?;:')}" for w in words if w.strip('.,!?;:') in CATEGORIES]
        return valid[:MAX_TAGS]
    except Exception as e:
        logger.warning(f"Failed to get tags for {article.url}: {e}")
        return []
