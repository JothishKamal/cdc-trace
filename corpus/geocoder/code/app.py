from geo import cache_geocode, clear_geocode_cache, lookup_geocode
from httpclient import build_geocode_request, build_geocode_url, geocode_fixture
from serialize import dump_geocode, load_geocode


def main():
    """Cache a fixture lookup and round-trip it through json."""
    query = "London"
    url = build_geocode_url(query)
    prepared = build_geocode_request(query)
    result = geocode_fixture(query)
    cache_geocode(query, result)
    hit = lookup_geocode(query)
    dumped = dump_geocode(hit)
    loaded = load_geocode(dumped)
    clear_geocode_cache()
    return {"url": url, "method": prepared.method, "loaded": loaded}


if __name__ == "__main__":
    main()
