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
    feed = feedparser.parse(source["url"])
    articles = []
    for entry in feed.entries:
        url = entry.get("link", "")
        title = entry.get("title", "")
        if url and title:
            articles.append(Article(title=title, url=url, source=source["name"]))
    return articles

async def fetch_all() -> list[Article]:
    articles = []
    for source in SOURCES:
        try:
            articles.extend(await fetch_feed(source))
        except Exception as e:
            print(f"[feeds] error fetching {source['name']}: {e}")
    return articles
