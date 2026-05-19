import os
import threading
import time

from fastapi import HTTPException, Request

MAX_REQUESTS: int = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
WINDOW_SECONDS: float = float(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))

_store: dict[str, tuple[int, float]] = {}
_lock = threading.Lock()


def _get_key(request: Request) -> str:
    user_id = request.headers.get("x-user-id")
    if user_id:
        return f"user:{user_id}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def check_rate_limit(request: Request) -> None:
    key = _get_key(request)
    now = time.time()
    limited = False
    retry_after = int(WINDOW_SECONDS) + 1
    try:
        with _lock:
            count, window_start = _store.get(key, (0, now))
            if now - window_start >= WINDOW_SECONDS:
                count, window_start = 0, now
            count += 1
            _store[key] = (count, window_start)
            if count > MAX_REQUESTS:
                limited = True
                retry_after = max(1, int(WINDOW_SECONDS - (now - window_start)) + 1)
    except Exception:
        return  # fail open
    if limited:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
