import json


def dump_feed(items):
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    payload = []
    for item in items:
        payload.append({
            "title": str(item.get("title", "")),
            "link": str(item.get("link", "")),
            "summary": str(item.get("summary", "")),
        })
    return json.dumps(payload)


def load_feed(text):
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
