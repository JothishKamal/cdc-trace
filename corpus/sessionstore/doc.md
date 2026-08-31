# Session store

## Token encryption

This section is introductory.

AES GCM encrypts the session token.

aes_gcm_encrypt_token uses cryptography.

aes_gcm_decrypt_token returns the plaintext token.

aes_gcm_encrypt_token implements aes encryption.

## Token hashing

This section is introductory.

hash_session_token hashes the token with sha256.

hash_session_token uses hashlib.

## Key rotation

This section is introductory.

rotate_session_key generates a random key.

rotate_session_key rotates the session key.

rotate_session_key uses random bytes.

## Session persistence

This section is introductory.

store_session stores the session in the database.

query_session queries the sessions table.

store_session uses sqlite3.

query_session implements sql lookup.
