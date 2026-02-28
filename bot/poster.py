from __future__ import annotations

import asyncio
import logging
from html import escape

from telegram import Bot
from telegram.error import RetryAfter

logger = logging.getLogger(__name__)

class Poster:
    def __init__(self, bot: Bot, channel_id: str):
        self._bot = bot
        self._channel_id = channel_id

    _MAX_RETRIES = 3

    async def post(self, summary: str, url: str, source: str = "", tags: list[str] | None = None):
        tags_line = ("\n" + " ".join(tags)) if tags else ""
        source_label = escape(source) if source else "Источник"
        link = f'<a href="{escape(url, quote=True)}">{source_label}</a>'
        text = f"{escape(summary)}{tags_line}\n\n{link}"
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                await self._bot.send_message(
                    chat_id=self._channel_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                return
            except RetryAfter as e:
                if attempt == self._MAX_RETRIES:
                    raise
                logger.warning(f"Telegram 429, retry {attempt}/{self._MAX_RETRIES} after {e.retry_after}s")
                await asyncio.sleep(e.retry_after)
