import hashlib
import json
import sqlite3


def warmup_bindings():
    return (hashlib, json, sqlite3)
