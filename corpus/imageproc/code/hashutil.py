import hashlib
import json


def hash_image(pixels):
    payload = json.dumps(pixels)
    digest = hashlib.sha256(payload.encode("utf-8"))
    return digest.hexdigest()


def hash_histogram(counts):
    payload = json.dumps(list(counts))
    digest = hashlib.sha256(payload.encode("utf-8"))
    return digest.hexdigest()
