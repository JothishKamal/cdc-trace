from parser import parse_feed, validate_feed
from serialize import dump_feed


class App:
    def route(self, path, **kwargs):
        def decorator(fn):
            return fn
        return decorator


app = App()


@app.route("/health")
def health():
    """Return a health payload for operators."""
    return {"status": "ok"}


@app.route("/feed")
def feed_endpoint():
    """Parse a sample feed and return json text under body."""
    raw = "Example|https://example.invalid/x|Hello"
    items = parse_feed(raw)
    if not validate_feed(items):
        return {"body": dump_feed([])}
    return {"body": dump_feed(items)}
