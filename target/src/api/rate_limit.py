import os
import time
from collections import defaultdict, deque
from math import ceil

from fastapi import Header, HTTPException, Request

_LIMIT = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))

_store: dict[str, deque] = defaultdict(deque)


def check_rate_limit(
    request: Request,
    x_user_id: int | None = Header(default=None),
) -> None:
    key = str(x_user_id) if x_user_id is not None else (
        request.client.host if request.client and request.client.host else "unknown"
    )
    now = time.monotonic()
    window = _store[key]

    while window and window[0] <= now - _WINDOW:
        window.popleft()

    if len(window) >= _LIMIT:
        retry_after = ceil(window[0] + _WINDOW - now)
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    window.append(now)
