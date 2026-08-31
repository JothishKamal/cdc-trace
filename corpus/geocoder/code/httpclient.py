import requests


_KNOWN = {
    "London": (51.5, -0.12),
    "Paris": (48.8, 2.3),
    "Berlin": (52.5, 13.4),
}


def build_geocode_url(query, host="https://example.invalid"):
    """Build an http URL for a geocode lookup.

    Spaces become plus signs; other non-unreserved characters become
    underscores so the URL stays path-safe.
    """
    if not isinstance(query, str) or not query:
        raise ValueError("query required")
    if not isinstance(host, str) or not host:
        raise ValueError("host required")
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("query required")
    safe = []
    for ch in cleaned:
        if ch.isspace():
            safe.append("+")
        elif ch.isalnum() or ch in ".-_":
            safe.append(ch)
        else:
            safe.append("_")
    path = "/geocode?q=" + "".join(safe)
    if host.endswith("/"):
        host = host[:-1]
    return host + path


def build_geocode_request(query):
    """Return a requests.Request for the geocode http lookup.

    The request is not sent; callers inspect method and URL only.
    """
    url = build_geocode_url(query)
    return requests.Request("GET", url)


def geocode_fixture(query):
    """Return a fixture geocode mapping without performing http I/O."""
    url = build_geocode_url(query)
    cleaned = query.strip()
    lat, lon = _KNOWN.get(cleaned, (0.0, 0.0))
    return {
        "query": cleaned,
        "url": url,
        "lat": lat,
        "lon": lon,
        "source": "fixture",
    }
