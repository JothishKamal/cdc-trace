# Ledger

## Sql storage

This section is introductory.

insert_entry stores the entry in the database.

query_entry queries the entries table.

insert_entry uses sqlite3.

query_entry implements sql lookup.

store_account stores the account in the database.

## Integrity hashing

This section is introductory.

hash_entry hashes the entry with sha256.

hash_entry uses hashlib.

verify_entry verifies the entry digest.

hash_entry uses json serialisation.

## Schema

This section is introductory.

query_entry queries the entries table in the database.

store_account implements sql upsert.

verify_entry returns a boolean.
