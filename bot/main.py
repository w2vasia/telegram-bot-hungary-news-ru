import asyncio
import logging
import os
import signal
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from bot.db import Database
from bot.translator.gemma import GemmaTranslator
from bot.poster import Poster
from bot.scheduler import run_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

async def main():
    bot_token = _require_env("TELEGRAM_BOT_TOKEN")
    channel_id = _require_env("TELEGRAM_CHANNEL_ID")

    db = Database()
    await db.init()

    translator = GemmaTranslator()
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

    stop_event = asyncio.Event()

    def _handle_signal():
        logger.info("Shutdown signal received.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    # Run immediately on startup, then wait for next scheduled run
    await run_once(db, translator, poster)

    await stop_event.wait()

    logger.info("Shutting down...")
    scheduler.shutdown(wait=False)
    await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
