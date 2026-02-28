import asyncio
import logging
from bot.db import Database
from bot.feeds import fetch_all
from bot.summarizer import summarize
from bot.translator.base import Translator
from bot.poster import Poster
from bot.tagger import get_tags

logger = logging.getLogger(__name__)

async def run_once(db: Database, translator: Translator, poster: Poster):
    articles = await fetch_all()
    for article in articles:
        if await db.is_seen(article.url):
            continue
        try:
            translated = await translator.translate(article.title)
            similar = await db.find_similar(translated)
            if similar:
                await db.mark_seen(article.url, title=translated)
                logger.info(f"Skipped duplicate: {article.url} (similar to: {similar!r})")
                continue
            summary = summarize(translated)
            tags = await get_tags(article, translator)
            await poster.post(summary=summary, url=article.url, source=article.source, tags=tags)
            await db.mark_seen(article.url, title=translated)
            logger.info(f"Posted: {article.url}")
            await asyncio.sleep(3)  # avoid Telegram flood control
        except Exception as e:
            logger.error(f"Failed to process {article.url}: {e}")
