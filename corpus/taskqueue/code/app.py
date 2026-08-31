from mac import sign_payload, verify_payload
from queue import enqueue_task, retry_task
from tokens import generate_queue_key, generate_task_id


def _ok():
    return "ok"


def main():
    """Sign a payload, enqueue a task, and retry a trivial callable."""
    key = generate_queue_key()
    task_id = generate_task_id()
    payload = b"task-body"
    signature = sign_payload(key, payload)
    ok = verify_payload(key, payload, signature)
    items = enqueue_task([], "demo", task_id)
    result = retry_task(_ok, 3)
    return {
        "ok": ok,
        "items": items,
        "result": result,
        "task_id": task_id,
    }


if __name__ == "__main__":
    main()
