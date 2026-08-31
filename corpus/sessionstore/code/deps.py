import cryptography
import hashlib
import secrets
import sqlite3


def warmup_bindings():
    return (cryptography, hashlib, secrets, sqlite3)
