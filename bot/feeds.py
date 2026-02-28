import asyncio
import feedparser
from dataclasses import dataclass

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

@dataclass
class Article:
    title: str
    url: str
    source: str

async def fetch_feed(source: dict) -> list[Article]:
    feed = await asyncio.to_thread(feedparser.parse, source["url"])
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
            print(f"[feeds] error fetching {source['name']}: {result}")
        else:
            articles.extend(result)
    return articles
