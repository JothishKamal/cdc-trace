from db import insert_entry, query_entry, store_account
from integrity import hash_entry, verify_entry


def test_insert_entry():
    digest = hash_entry("a1", 10)
    insert_entry("a1", 10, digest)


def test_query_entry():
    digest = hash_entry("a1", 10)
    entry_id = insert_entry("a1", 10, digest)
    query_entry(entry_id)


def test_store_account():
    store_account("a1", "cash", 0)


def test_hash_entry():
    hash_entry("a1", 10)


def test_verify_entry():
    digest = hash_entry("a1", 10)
    verify_entry("a1", 10, digest)
