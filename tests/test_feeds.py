# tests/test_feeds.py
from bot.feeds import SOURCES, Article


def test_sources_has_eight_entries():
    assert len(SOURCES) == 8

def test_sources_all_have_name_and_url():
    for source in SOURCES:
        assert "name" in source
        assert "url" in source

def test_article_fields():
    a = Article(title="T", url="http://x.com", source="MTI")
    assert a.title == "T"
    assert a.url == "http://x.com"
    assert a.source == "MTI"

