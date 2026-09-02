import json
import re


_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def dump_feed(items):
    """Return json text for a list of feed items.

    Control characters are stripped before json dumps so the payload is
    safe to echo on a page.
    """
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    payload = []
    for item in items:
        title = _CTRL.sub("", str(item.get("title", "")))
        link = _CTRL.sub("", str(item.get("link", "")))
        summary = _CTRL.sub("", str(item.get("summary", "")))
        payload.append({
            "title": title,
            "link": link,
            "summary": summary,
        })
    return json.dumps(payload)


def load_feed(text):
    """Parse json payloads back into feed item mappings."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("payload must be a list")
    items = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        items.append({
            "title": str(item.get("title", "")),
            "link": str(item.get("link", "")),
            "summary": str(item.get("summary", "")),
        })
    return items
