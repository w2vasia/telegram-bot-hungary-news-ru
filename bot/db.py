from __future__ import annotations
import asyncio
import os
from typing import Optional
import aiosqlite
from rapidfuzz.fuzz import token_sort_ratio

class Database:
    def __init__(self, path: str = "data/seen.db"):
        self.path = str(path)
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def init(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        await self._conn.execute(
            "CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY)"
        )
        # migrate: add title and posted_at columns
        cursor = await self._conn.execute("PRAGMA table_info(seen_urls)")
        cols = {row[1] for row in await cursor.fetchall()}
        if "title" not in cols:
            await self._conn.execute("ALTER TABLE seen_urls ADD COLUMN title TEXT DEFAULT ''")
        if "posted_at" not in cols:
            await self._conn.execute(
                "ALTER TABLE seen_urls ADD COLUMN posted_at TIMESTAMP DEFAULT NULL"
            )
        else:
            await self._conn.execute("UPDATE seen_urls SET posted_at = NULL WHERE posted_at = ''")
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_posted_at ON seen_urls(posted_at)"
        )
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def is_seen(self, url: str) -> bool:
        async with self._conn.execute(
            "SELECT 1 FROM seen_urls WHERE url = ?", (url,)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def mark_seen(self, url: str, title: str = ""):
        async with self._lock:
            await self._conn.execute(
                "INSERT INTO seen_urls (url, title, posted_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(url) DO UPDATE SET title=excluded.title, posted_at=excluded.posted_at",
                (url, title),
            )
            await self._conn.commit()

    async def prune(self, keep_days: int = 30):
        async with self._lock:
            await self._conn.execute(
                "DELETE FROM seen_urls WHERE posted_at < datetime('now', ?)",
                (f"-{keep_days} days",),
            )
            await self._conn.commit()

    async def find_similar(self, title: str, threshold: int = 80, hours: int = 24) -> Optional[str]:
        async with self._lock:
            async with self._conn.execute(
                "SELECT title FROM seen_urls WHERE title != '' "
                "AND posted_at >= datetime('now', ?) "
                "ORDER BY posted_at DESC LIMIT 5000",
                (f"-{hours} hours",),
            ) as cursor:
                rows = await cursor.fetchall()
        for (existing,) in rows:
            if token_sort_ratio(title, existing) >= threshold:
                return existing
        return None
