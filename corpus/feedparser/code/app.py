from parser import parse_feed, validate_feed
from routes import feed_endpoint, health
from serialize import dump_feed, load_feed


def main():
    raw = "Alpha|https://example.invalid/a|One\nBeta|https://example.invalid/b|Two"
    items = parse_feed(raw)
    ok = validate_feed(items)
    dumped = dump_feed(items)
    loaded = load_feed(dumped)
    status = health()
    page = feed_endpoint()
    return {
        "ok": ok,
        "loaded": loaded,
        "status": status,
        "page": page,
    }


if __name__ == "__main__":
    main()
