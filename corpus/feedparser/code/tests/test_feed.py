from parser import parse_feed, validate_feed
from routes import feed_endpoint, health
from serialize import dump_feed, load_feed


def test_parse_feed():
    items = parse_feed("Title|https://example.invalid/t|Sum")
    assert isinstance(items, list)


def test_validate_feed():
    validate_feed([{"title": "T", "link": "https://example.invalid/t"}])


def test_dump_feed():
    dump_feed([{"title": "T", "link": "L", "summary": "S"}])


def test_load_feed():
    load_feed('[{"title": "T", "link": "L", "summary": "S"}]')


def test_health():
    health()


def test_feed_endpoint():
    feed_endpoint()
