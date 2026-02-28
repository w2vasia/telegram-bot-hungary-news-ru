import asyncio
import logging
import socket
import feedparser
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SOURCES = [
    {"name": "Telex", "url": "https://telex.hu/rss"},
    {"name": "HVG", "url": "https://hvg.hu/rss"},
    {"name": "24.hu", "url": "https://24.hu/feed/"},
    {"name": "444", "url": "https://444.hu/feed"},
    {"name": "Direkt36", "url": "https://www.direkt36.hu/feed/"},
    {"name": "Átlátszó", "url": "https://atlatszo.hu/feed/"},
    {"name": "Portfolio", "url": "https://www.portfolio.hu/rss/all.xml"},
    {"name": "G7", "url": "https://telex.hu/rss/g7"},
]

_FEED_TIMEOUT = 30

@dataclass
class Article:
    title: str
    url: str
    source: str

def _parse_with_timeout(url: str):
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(_FEED_TIMEOUT)
        return feedparser.parse(url)
    finally:
        socket.setdefaulttimeout(old_timeout)

async def fetch_feed(source: dict) -> list[Article]:
    feed = await asyncio.wait_for(
        asyncio.to_thread(_parse_with_timeout, source["url"]),
        timeout=_FEED_TIMEOUT + 5,
    )
    if feed.bozo and not feed.entries:
        logger.warning(f"Feed {source['name']} failed: {feed.bozo_exception}")
        return []
    articles = []
    for entry in feed.entries:
        url = entry.get("link", "")
        title = entry.get("title", "")
        if url and title:
            articles.append(Article(title=title, url=url, source=source["name"]))
    return articles

async def fetch_all() -> list[Article]:
    results = await asyncio.gather(
        *[fetch_feed(source) for source in SOURCES],
        return_exceptions=True,
    )
    articles = []
    for source, result in zip(SOURCES, results):
        if isinstance(result, Exception):
            logger.error(f"Error fetching {source['name']}: {result}")
        else:
            articles.extend(result)
    return articles
