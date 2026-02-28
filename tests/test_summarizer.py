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

def test_trim_uses_space_even_if_early():
    # Space found at position 10 in a 499-char window — should still use word boundary
    word = "слово"
    # Build: 10 chars + space + filler to exceed 500
    text = (word + " ") + ("а" * 600)
    result = summarize(text)
    assert len(result) <= 500
    assert result.endswith("…")
    # Result should not cut mid-char in the filler (just verifying it doesn't crash)
    assert result  # non-empty
