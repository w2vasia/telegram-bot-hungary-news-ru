# tests/test_summarizer.py
from bot.summarizer import summarize

def test_short_text_unchanged():
    text = "Короткий текст."
    assert summarize(text) == text

def test_long_text_trimmed_to_500():
    text = "А" * 600
    result = summarize(text)
    assert len(result) <= 500

def test_trimmed_ends_with_ellipsis():
    text = "А" * 600
    result = summarize(text)
    assert result.endswith("…")

def test_trim_at_word_boundary():
    # words separated by spaces, trim should not cut mid-word
    text = " ".join(["слово"] * 120)  # well over 500 chars
    result = summarize(text)
    assert not result.rstrip("…").endswith(" ")
    assert "слово" in result
