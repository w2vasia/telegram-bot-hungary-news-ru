import aiosqlite

class Database:
    def __init__(self, path: str = "data/seen.db"):
        self.path = str(path)

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY)"
            )
            await db.commit()

    async def is_seen(self, url: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT 1 FROM seen_urls WHERE url = ?", (url,)
            ) as cursor:
                return await cursor.fetchone() is not None

    async def mark_seen(self, url: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO seen_urls (url) VALUES (?)", (url,)
            )
            await db.commit()
