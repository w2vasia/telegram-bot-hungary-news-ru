import asyncio
import logging
import os

from rapidfuzz.fuzz import token_sort_ratio

from bot.db import Database
from bot.feeds import fetch_all
from bot.poster import Poster
from bot.summarizer import summarize
from bot.tagger import get_tags
from bot.translator.base import Translator

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 80
_prune_fail_count = 0
_PRUNE_FAIL_LIMIT = 10
_POST_DELAY = float(os.environ.get("POST_DELAY", "3"))


async def run_once(db: Database, translator: Translator, poster: Poster):
    global _prune_fail_count
    # Prune old entries periodically
    try:
        await db.prune()
        _prune_fail_count = 0
    except Exception as e:
        _prune_fail_count += 1
        if _prune_fail_count >= _PRUNE_FAIL_LIMIT:
            logger.error(f"DB prune failed {_prune_fail_count} times consecutively: {e}")
            raise
        logger.warning(f"DB prune failed ({_prune_fail_count}/{_PRUNE_FAIL_LIMIT}): {e}")

    # Phase 1: Fetch all articles from all sources concurrently
    try:
        articles = await fetch_all()
    except Exception as e:
        logger.error(f"Feed fetch failed entirely: {e}")
        return
    logger.info(f"Fetched {len(articles)} articles.")

    # Phase 2: Filter already-seen URLs in parallel
    seen_results = await asyncio.gather(
        *[db.is_seen(a.url) for a in articles], return_exceptions=True
    )
    new_articles = []
    for article, result in zip(articles, seen_results):
        if isinstance(result, Exception):
            logger.warning(f"is_seen check failed for {article.url}: {result}")
            new_articles.append(article)  # assume unseen on error
        elif not result:
            new_articles.append(article)
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
            try:
                if await db.find_similar(translated):
                    try:
                        await db.mark_seen(article.url, title=translated)
                    except Exception as e:
                        logger.warning(f"Failed to mark dupe seen {article.url}: {e}")
                    logger.info(f"Skipped (DB duplicate): {article.url}")
                    continue
            except Exception as e:
                logger.warning(f"find_similar failed for {article.url}: {e}")

            # Deduplicate within this batch
            if any(token_sort_ratio(translated, t) >= _SIMILARITY_THRESHOLD for t in accepted_titles):
                try:
                    await db.mark_seen(article.url, title=translated)
                except Exception as e:
                    logger.warning(f"Failed to mark batch dupe seen {article.url}: {e}")
                logger.info(f"Skipped (batch duplicate): {article.url}")
                continue

            accepted_titles.append(translated)
            to_post.append((article, translated))

        except Exception as e:
            logger.error(f"Translation failed for {article.url}: {e}")

    logger.info(f"{len(to_post)} unique articles to post.")

    # Phase 4: Post verified unique articles — mark seen first to prevent duplicates
    for article, translated in to_post:
        try:
            await db.mark_seen(article.url, title=translated)
        except Exception as e:
            logger.error(f"Failed to mark seen before post {article.url}: {e}")
            continue  # skip posting if we can't guarantee dedup

        try:
            summary = summarize(translated)
            tags = await get_tags(translated, translator)
            await poster.post(summary=summary, url=article.url, source=article.source, tags=tags)
        except Exception as e:
            logger.error(f"Failed to post {article.url}: {e}")
            continue

        logger.info(f"Posted: {article.url}")
        await asyncio.sleep(_POST_DELAY)
