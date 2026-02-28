# tests/test_feeds.py
import pytest
from bot.feeds import Article, fetch_feed, SOURCES

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

def test_article_has_raw_categories():
    a = Article(title="T", url="http://x.com", source="MTI", raw_categories=["belfold", "gazdasag"])
    assert a.raw_categories == ["belfold", "gazdasag"]

def test_article_raw_categories_defaults_to_empty():
    a = Article(title="T", url="http://x.com", source="MTI")
    assert a.raw_categories == []
