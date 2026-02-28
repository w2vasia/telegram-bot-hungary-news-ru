from telegram import Bot

class Poster:
    def __init__(self, bot: Bot, channel_id: str):
        self._bot = bot
        self._channel_id = channel_id

    async def post(self, summary: str, url: str):
        text = f"{summary}\n\n<a href='{url}'>Читать полностью</a>"
        await self._bot.send_message(
            chat_id=self._channel_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
