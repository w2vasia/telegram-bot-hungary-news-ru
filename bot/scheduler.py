import asyncio
import logging
from rapidfuzz.fuzz import token_sort_ratio
from bot.db import Database
from bot.feeds import fetch_all
from bot.summarizer import summarize
from bot.translator.base import Translator
from bot.poster import Poster
from bot.tagger import get_tags

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 80


async def run_once(db: Database, translator: Translator, poster: Poster):
    # Phase 1: Fetch all articles from all sources concurrently
    articles = await fetch_all()
    logger.info(f"Fetched {len(articles)} articles.")

    # Phase 2: Filter already-seen URLs in parallel
    seen_flags = await asyncio.gather(*[db.is_seen(a.url) for a in articles])
    new_articles = [a for a, seen in zip(articles, seen_flags) if not seen]
    logger.info(f"{len(new_articles)} new articles after URL filter.")

    if not new_articles:
        return

    # Phase 3: Translate and build deduplicated post list
    to_post: list[tuple] = []
    accepted_titles: list[str] = []

    for article in new_articles:
        try:
            translated = await translator.translate(article.title)

            # Deduplicate against DB (last 24h)
            if await db.find_similar(translated):
                await db.mark_seen(article.url, title=translated)
                logger.info(f"Skipped (DB duplicate): {article.url}")
                continue

            # Deduplicate within this batch
            if any(token_sort_ratio(translated, t) >= _SIMILARITY_THRESHOLD for t in accepted_titles):
                await db.mark_seen(article.url, title=translated)
                logger.info(f"Skipped (batch duplicate): {article.url}")
                continue

            accepted_titles.append(translated)
            to_post.append((article, translated))

        except Exception as e:
            logger.error(f"Translation failed for {article.url}: {e}")

    logger.info(f"{len(to_post)} unique articles to post.")

    # Phase 4: Post verified unique articles
    for article, translated in to_post:
        try:
            summary = summarize(translated)
            tags = await get_tags(article, translator)
            await poster.post(summary=summary, url=article.url, source=article.source, tags=tags)
            await db.mark_seen(article.url, title=translated)
            logger.info(f"Posted: {article.url}")
            await asyncio.sleep(3)  # avoid Telegram flood control
        except Exception as e:
            logger.error(f"Failed to post {article.url}: {e}")
