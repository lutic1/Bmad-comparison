# Data Model: API Rate Limiting

**Feature**: `001-api-rate-limiting`
**Date**: 2026-05-19

## Overview

Rate limiting uses only in-memory state. No database tables are added or modified.
All structures live within the middleware instance and are discarded on process restart.

## In-Memory State

### Counter Store

```
_counters: dict[tuple[str, int], int]
```

- **Key**: `(scope_key, window_start)` where:
  - `scope_key` — string identifying the client: user ID (from `X-User-Id` header)
    or IP address (from `request.client.host`) when no user header is present.
  - `window_start` — Unix timestamp (integer seconds) of when the current window began,
    derived as `floor(current_time / window_seconds) * window_seconds`.
- **Value**: integer count of requests made by this scope in this window.
- **Concurrency**: reads and writes are protected by a single `threading.Lock` instance.

### State Lifecycle

- Entries are created on first request from a scope within a window.
- Old window entries are never explicitly deleted (minor memory leak for long-lived
  processes with many unique scopes). Acceptable for this service's scale; a cleanup
  pass can be added later if needed.

## Pydantic Schemas (New)

### `RateLimitError` (response body for 429)

```python
class RateLimitError(BaseModel):
    detail: str        # Always "Rate limit exceeded"
    retry_after: int   # Seconds until the current window resets
```

Lives in `src/api/middleware/rate_limiter.py` alongside the middleware class.

## HTTP Response Headers (all responses)

| Header                  | Type    | Description                                        |
|-------------------------|---------|----------------------------------------------------|
| `X-RateLimit-Limit`     | integer | Configured quota per window                        |
| `X-RateLimit-Remaining` | integer | Requests remaining in current window (min 0)       |
| `X-RateLimit-Reset`     | integer | Unix timestamp when the current window resets      |
| `Retry-After`           | integer | Seconds until reset — present on 429 responses only|

## Scope Resolution Logic

```
if "X-User-Id" in request.headers:
    scope_key = f"user:{request.headers['X-User-Id']}"
else:
    scope_key = f"ip:{request.client.host}"
```

Prefixing with `user:` / `ip:` avoids collisions between a user ID that happens to
match an IP address string.

## No Database Changes

- `User`, `Order`, and `OrderItem` models are unchanged.
- No migrations needed.
