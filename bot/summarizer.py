MAX_CHARS = 500

def summarize(text: str) -> str:
    text = text.strip()
    if len(text) <= MAX_CHARS:
        return text
    truncated = text[:MAX_CHARS - 1]
    last_space = truncated.rfind(" ")
    if last_space != -1:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "…"
