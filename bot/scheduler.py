import logging
from bot.db import Database
from bot.feeds import fetch_all
from bot.summarizer import summarize
from bot.translator.base import Translator
from bot.poster import Poster

logger = logging.getLogger(__name__)

async def run_once(db: Database, translator: Translator, poster: Poster):
    articles = await fetch_all()
    for article in articles:
        if await db.is_seen(article.url):
            continue
        try:
            translated = await translator.translate(article.title)
            summary = summarize(translated)
            await poster.post(summary=summary, url=article.url)
            await db.mark_seen(article.url)
            logger.info(f"Posted: {article.url}")
        except Exception as e:
            logger.error(f"Failed to process {article.url}: {e}")
