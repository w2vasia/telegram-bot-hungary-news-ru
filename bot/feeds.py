import feedparser
from dataclasses import dataclass

SOURCES = [
    {"name": "MTI", "url": "https://www.mti.hu/rss/"},
    {"name": "Index", "url": "https://index.hu/24ora/rss/"},
    {"name": "444", "url": "https://444.hu/feed"},
    {"name": "Telex", "url": "https://telex.hu/rss"},
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
