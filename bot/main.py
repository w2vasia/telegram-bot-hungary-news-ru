import asyncio
import logging
import os
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from bot.db import Database
from bot.poster import Poster
from bot.scheduler import run_once
from bot.translator.gemma import OLLAMA_URL, GemmaTranslator

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_STARTUP_TIMEOUT = float(os.environ.get("STARTUP_TIMEOUT", "300"))

def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

async def _check_ollama():
    """Verify Ollama is reachable. Raises on failure."""
    import httpx
    base = OLLAMA_URL.rsplit("/", 2)[0]  # strip /api/generate
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(base)
            resp.raise_for_status()
        logger.info("Ollama health check passed.")
    except Exception as e:
        raise RuntimeError(f"Ollama not reachable at {base}: {e}") from e

async def _check_telegram(bot: Bot):
    """Verify Telegram bot token is valid. Raises on failure."""
    try:
        me = await bot.get_me()
        logger.info(f"Telegram health check passed: @{me.username}")
    except Exception as e:
        raise RuntimeError(f"Telegram health check failed: {e}") from e

async def main():
    bot_token = _require_env("TELEGRAM_BOT_TOKEN")
    channel_id = _require_env("TELEGRAM_CHANNEL_ID")

    db = Database()
    await db.init()

    translator = GemmaTranslator()
    bot = Bot(token=bot_token)
    poster = Poster(bot=bot, channel_id=channel_id)

    stop_event = asyncio.Event()

    def _handle_signal():
        logger.info("Shutdown signal received.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    # Startup health checks
    await asyncio.gather(_check_ollama(), _check_telegram(bot))

    # Run immediately on startup with timeout
    try:
        await asyncio.wait_for(run_once(db, translator, poster), timeout=_STARTUP_TIMEOUT)
    except TimeoutError:
        logger.error(f"Initial run_once timed out after {_STARTUP_TIMEOUT}s")
    except Exception as e:
        logger.error(f"Initial run_once failed: {e}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_once,
        "interval",
        minutes=30,
        args=[db, translator, poster],
        max_instances=1,
        misfire_grace_time=900,  # run if ≤15 min late
        coalesce=True,           # merge piled-up runs into one
    )
    scheduler.start()
    logger.info("Bot started. Polling every 30 minutes.")

    await stop_event.wait()

    logger.info("Shutting down...")
    scheduler.shutdown(wait=True)
    await translator.close()
    await db.close()
    await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
