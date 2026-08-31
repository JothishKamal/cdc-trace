import json


def dump_image_meta(pixels, digest):
    payload = {
        "height": len(pixels),
        "width": len(pixels[0]) if pixels else 0,
        "digest": digest,
    }
    return json.dumps(payload)


def load_image_meta(text):
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("payload must be an object")
    return {
        "height": int(parsed.get("height", 0)),
        "width": int(parsed.get("width", 0)),
        "digest": str(parsed.get("digest", "")),
    }
