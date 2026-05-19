import threading
import time

from fastapi import HTTPException, Request

WINDOW = 60   # seconds
LIMIT = 60    # requests per window

_lock = threading.Lock()
_counters: dict[str, tuple[int, float]] = {}


def rate_limit(request: Request) -> None:
    key = request.headers.get("x-user-id") or (
        request.client.host if request.client else "unknown"
    )
    now = time.monotonic()
    with _lock:
        count, window_start = _counters.get(key, (0, now))
        if now - window_start >= WINDOW:
            count, window_start = 0, now
        if count >= LIMIT:
            retry_after = int(WINDOW - (now - window_start))
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )
        _counters[key] = (count + 1, window_start)
