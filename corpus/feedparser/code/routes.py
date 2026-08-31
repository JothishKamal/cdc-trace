class App:
    def route(self, path, **kwargs):
        def decorator(fn):
            return fn
        return decorator


app = App()


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/feed")
def feed_endpoint():
    from parser import parse_feed
    from serialize import dump_feed
    items = parse_feed("Example|https://example.invalid/x|Hello")
    body = dump_feed(items)
    return {"body": body}
