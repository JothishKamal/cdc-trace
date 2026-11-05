from mac import sign_payload, verify_payload
from queue import enqueue_task, retry_task
from tokens import generate_queue_key, generate_task_id


def test_sign_payload():
    key = generate_queue_key()
    sign_payload(key, b"body")


def test_verify_payload():
    key = generate_queue_key()
    sig = sign_payload(key, b"body")
    verify_payload(key, b"body", sig)


def test_enqueue_task():
    enqueue_task([], "demo", b"x")


def test_retry_task():
    retry_task(lambda: 1, 2)


def test_generate_task_id():
    generate_task_id()


def test_generate_queue_key():
    generate_queue_key()
