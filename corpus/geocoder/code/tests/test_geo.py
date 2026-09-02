from geo import cache_geocode, clear_geocode_cache, lookup_geocode
from httpclient import build_geocode_request, build_geocode_url, geocode_fixture
from serialize import dump_geocode, load_geocode


def test_cache_geocode():
    cache_geocode("Paris", {"lat": 48.8, "lon": 2.3})


def test_lookup_geocode():
    cache_geocode("Paris", {"lat": 48.8, "lon": 2.3})
    lookup_geocode("Paris")


def test_build_geocode_url():
    build_geocode_url("Paris")


def test_build_geocode_request():
    build_geocode_request("Paris")


def test_geocode_fixture():
    geocode_fixture("Paris")


def test_dump_geocode():
    dump_geocode({"query": "Paris", "lat": 48.8, "lon": 2.3})


def test_load_geocode():
    load_geocode('{"query": "Paris", "lat": 48.8, "lon": 2.3}')


def test_clear_geocode_cache():
    clear_geocode_cache()
