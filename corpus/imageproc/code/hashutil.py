import hashlib
import json


def hash_image(pixels):
    """Hash an image with sha256 over its json encoding.

    The function uses hashlib so two equal arrays share a digest.
    """
    payload = json.dumps(pixels)
    digest = hashlib.sha256(payload.encode("utf-8"))
    return digest.hexdigest()


def hash_histogram(counts):
    """Hash a histogram with sha256 over a json list of counts."""
    payload = json.dumps(list(counts))
    digest = hashlib.sha256(payload.encode("utf-8"))
    return digest.hexdigest()
