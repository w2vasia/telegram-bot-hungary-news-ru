# tests/test_feeds.py
import pytest
from bot.feeds import Article, fetch_feed, SOURCES

def test_sources_has_four_entries():
    assert len(SOURCES) == 4

def test_sources_all_have_name_and_url():
    for source in SOURCES:
        assert "name" in source
        assert "url" in source

def test_article_fields():
    a = Article(title="T", url="http://x.com", source="MTI")
    assert a.title == "T"
    assert a.url == "http://x.com"
    assert a.source == "MTI"
