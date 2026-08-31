def enqueue_task(queue, name, payload):
    if queue is None:
        queue = []
    if not isinstance(queue, list):
        raise TypeError("queue must be a list")
    if not isinstance(name, str) or not name:
        raise ValueError("name required")
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("name required")
    if len(cleaned) > 128:
        raise ValueError("name too long")
    for ch in cleaned:
        if ch.isspace():
            raise ValueError("name must not contain spaces")
    item = {
        "name": cleaned,
        "payload": payload,
        "attempts": 0,
        "state": "queued",
    }
    queue.append(item)
    return item


def retry_task(task, attempts):
    if not callable(task):
        raise TypeError("task must be callable")
    if attempts < 1:
        raise ValueError("attempts must be positive")
    limit = int(attempts)
    if limit > 32:
        raise ValueError("attempts too large")
    last_error = None
    for step in range(limit):
        try:
            result = task()
            if result is None and step + 1 < limit:
                continue
            return result
        except Exception as exc:
            last_error = exc
            if step + 1 >= limit:
                break
    if last_error is None:
        raise RuntimeError("retry exhausted")
    raise last_error
