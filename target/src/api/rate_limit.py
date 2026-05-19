import time

from fastapi import Depends, Header, HTTPException, Response


class RateLimiter:
    def __init__(self, limit: int = 100, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._counts: dict[int, tuple[int, float]] = {}

    def check(self, user_id: int, response: Response) -> None:
        now = time.time()
        count, window_start = self._counts.get(user_id, (0, now))

        if now - window_start >= self.window_seconds:
            count, window_start = 0, now

        reset_at = int(window_start + self.window_seconds)

        if count >= self.limit:
            retry_after = max(0, reset_at - int(now))
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                },
            )

        count += 1
        self._counts[user_id] = (count, window_start)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(self.limit - count)
        response.headers["X-RateLimit-Reset"] = str(reset_at)


_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter


def check_rate_limit(
    response: Response,
    x_user_id: int | None = Header(default=None),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    if x_user_id is None:
        return
    limiter.check(x_user_id, response)
