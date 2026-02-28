import logging
from bot.feeds import Article
from bot.translator.base import Translator

logger = logging.getLogger(__name__)

MAX_TAGS = 3

def _format_tags(raw: str) -> list[str]:
    words = raw.lower().split()
    tags = []
    for w in words:
        w = w.strip(".,!?;:")
        if w:
            tags.append(f"#{w}")
    return tags[:MAX_TAGS]

async def get_tags(article: Article, translator: Translator) -> list[str]:
    try:
        if article.raw_categories:
            categories_str = " ".join(article.raw_categories[:MAX_TAGS])
            prompt = (
                f"Translate these Hungarian category names to single Russian words "
                f"suitable as hashtags, space-separated. Return only the words: {categories_str}"
            )
        else:
            prompt = (
                f"Classify this Hungarian news headline into 1-3 single Russian words "
                f"(e.g. политика, экономика, спорт, культура, технологии, общество, мир). "
                f"Return only the words space-separated: {article.title}"
            )
        result = await translator.translate(prompt, source_lang="HU", target_lang="RU")
        return _format_tags(result)
    except Exception as e:
        logger.warning(f"Failed to get tags for {article.url}: {e}")
        return []
