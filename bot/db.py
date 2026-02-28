import os
from typing import Optional
import aiosqlite
from rapidfuzz.fuzz import token_sort_ratio

class Database:
    def __init__(self, path: str = "data/seen.db"):
        self.path = str(path)

    async def init(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY)"
            )
            # migrate: add title and posted_at columns
            cursor = await db.execute("PRAGMA table_info(seen_urls)")
            cols = {row[1] for row in await cursor.fetchall()}
            if "title" not in cols:
                await db.execute("ALTER TABLE seen_urls ADD COLUMN title TEXT DEFAULT ''")
            if "posted_at" not in cols:
                await db.execute(
                    "ALTER TABLE seen_urls ADD COLUMN posted_at TIMESTAMP DEFAULT ''"
                )
            await db.commit()

    async def is_seen(self, url: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT 1 FROM seen_urls WHERE url = ?", (url,)
            ) as cursor:
                return await cursor.fetchone() is not None

    async def mark_seen(self, url: str, title: str = ""):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO seen_urls (url, title, posted_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (url, title),
            )
            await db.commit()

    async def find_similar(self, title: str, threshold: int = 80, hours: int = 24) -> Optional[str]:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT title FROM seen_urls WHERE title != '' AND posted_at >= datetime('now', ?)",
                (f"-{hours} hours",),
            ) as cursor:
                rows = await cursor.fetchall()
        for (existing,) in rows:
            if token_sort_ratio(title, existing) >= threshold:
                return existing
        return None
