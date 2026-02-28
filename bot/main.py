import asyncio
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from bot.db import Database
# TODO: switch to DeepLTranslator once DEEPL_API_KEY is configured
from bot.translator.stub import StubTranslator
from bot.poster import Poster
from bot.scheduler import run_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

async def main():
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]

    db = Database()
    await db.init()

    translator = StubTranslator()
    bot = Bot(token=bot_token)
    poster = Poster(bot=bot, channel_id=channel_id)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_once,
        "interval",
        minutes=30,
        args=[db, translator, poster],
    )
    scheduler.start()

    logger.info("Bot started. Polling every 30 minutes.")
    # Run immediately on startup
    await run_once(db, translator, poster)

    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
