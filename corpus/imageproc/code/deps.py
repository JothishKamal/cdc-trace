import hashlib
import json


def warmup_bindings():
    return (hashlib, json)
