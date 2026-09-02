import json


def dump_geocode(result):
    """Return json text for a geocode mapping."""
    if not isinstance(result, dict):
        raise TypeError("result must be a dict")
    payload = {
        "query": str(result.get("query", "")),
        "lat": float(result.get("lat", 0.0)),
        "lon": float(result.get("lon", 0.0)),
    }
    return json.dumps(payload)


def load_geocode(text):
    """Parse json payloads into a geocode mapping with lat and lon."""
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("payload must be an object")
    return {
        "query": str(parsed.get("query", "")),
        "lat": float(parsed.get("lat", 0.0)),
        "lon": float(parsed.get("lon", 0.0)),
    }
