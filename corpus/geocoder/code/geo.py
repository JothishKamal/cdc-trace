_CACHE = {}
_MAX_CACHE = 256


def cache_geocode(query, result):
    if not isinstance(query, str) or not query:
        raise ValueError("query required")
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("query required")
    if len(cleaned) > 200:
        raise ValueError("query too long")
    if not isinstance(result, dict):
        raise TypeError("result must be a dict")
    if "lat" not in result or "lon" not in result:
        raise ValueError("result must include lat and lon")
    if len(_CACHE) >= _MAX_CACHE and cleaned not in _CACHE:
        oldest = next(iter(_CACHE))
        del _CACHE[oldest]
    _CACHE[cleaned] = {
        "query": cleaned,
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
    }
    return _CACHE[cleaned]


def lookup_geocode(query):
    if not isinstance(query, str) or not query:
        raise ValueError("query required")
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("query required")
    if cleaned in _CACHE:
        hit = _CACHE[cleaned]
        return {
            "query": hit["query"],
            "lat": hit["lat"],
            "lon": hit["lon"],
        }
    return None


def clear_geocode_cache():
    keys = list(_CACHE.keys())
    for key in keys:
        del _CACHE[key]
    return len(_CACHE)
