import os
import threading
import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, float]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                retry_after = q[0] + self.window_seconds - now
                return False, max(retry_after, 0.0)
            q.append(now)
            return True, 0.0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def _build_default_limiter() -> SlidingWindowLimiter:
    per_minute = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
    return SlidingWindowLimiter(max_requests=per_minute, window_seconds=60.0)


limiter = _build_default_limiter()
