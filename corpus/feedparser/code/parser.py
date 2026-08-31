import re


FEED_LINE = re.compile(
    r"^(?P<title>[^|]+)\|(?P<link>[^|]+)\|(?P<summary>.*)$"
)
TAG = re.compile(r"<[^>]+>")


def parse_feed(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    items = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = FEED_LINE.match(line)
        if match is None:
            continue
        items.append({
            "title": match.group("title").strip(),
            "link": match.group("link").strip(),
            "summary": match.group("summary").strip(),
        })
    return items


def validate_feed(items):
    if not isinstance(items, list):
        return False
    for item in items:
        if not isinstance(item, dict):
            return False
        title = item.get("title")
        link = item.get("link")
        if not title or not link:
            return False
        if TAG.search(str(title)) is not None:
            return False
    return True
