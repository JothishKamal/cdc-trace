import secrets


TASK_ID_SIZE = 16
QUEUE_KEY_SIZE = 32


def generate_task_id():
    blob = secrets.token_bytes(TASK_ID_SIZE)
    if len(blob) != TASK_ID_SIZE:
        raise RuntimeError("task id size mismatch")
    if blob == b"\x00" * TASK_ID_SIZE:
        blob = secrets.token_bytes(TASK_ID_SIZE)
    return blob


def generate_queue_key():
    blob = secrets.token_bytes(QUEUE_KEY_SIZE)
    if len(blob) != QUEUE_KEY_SIZE:
        raise RuntimeError("queue key size mismatch")
    if blob == b"\x00" * QUEUE_KEY_SIZE:
        blob = secrets.token_bytes(QUEUE_KEY_SIZE)
    return blob
