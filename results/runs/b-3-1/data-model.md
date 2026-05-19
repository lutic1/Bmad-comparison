# Data Model: API Rate Limiting

**Feature**: 001-api-rate-limiting
**Date**: 2026-05-18

---

## Overview

Rate limiting state is held entirely in-memory. No database schema changes are required. Two logical structures exist: the configuration (static) and the per-client tracking records (mutable).

---

## RateLimitRule (configuration)

Defines the policy applied uniformly to all clients.

| Field            | Type  | Description                                      |
|------------------|-------|--------------------------------------------------|
| `limit`          | int   | Maximum requests allowed per window. Default 100 |
| `window_seconds` | int   | Duration of each window in seconds. Default 60   |

Instantiated once at application startup. Configurable via constructor arguments to support test overrides.

---

## ClientRequestRecord (in-memory tracking)

One record per active client. Stored in a `dict[int, tuple[int, float]]` keyed by `user_id`.

| Field          | Type  | Description                                               |
|----------------|-------|-----------------------------------------------------------|
| `user_id`      | int   | Client identifier (value of `X-User-Id` header). Map key |
| `count`        | int   | Number of requests made in the current window             |
| `window_start` | float | Unix timestamp (seconds) when the current window began    |

**Lifecycle**:
- Record is created on the client's first request.
- `count` increments on each subsequent request within the same window.
- When `now - window_start >= window_seconds`, both `count` and `window_start` reset.
- Records for expired windows are lazily reset on the next request from that client (no background cleanup thread required at this scale).

---

## State Transitions

```
[no record]
     │  first request from user_id
     ▼
[count=1, window_start=now]
     │  subsequent requests within window (count < limit)
     ▼
[count=N, window_start=T]  ──→  count < limit: allow, increment
                            ──→  count >= limit: reject 429
     │  request arrives after window expired (now - T >= window_seconds)
     ▼
[count=1, window_start=now]   ← window reset, request allowed
```

---

## Notes

- No persistent storage. State is lost on restart (acceptable per spec assumptions).
- Thread safety: CPython's GIL provides adequate protection for simple dict operations in a synchronous WSGI/ASGI context with a single worker. No locking primitives needed at this scale.
- Memory bound: one `(int, float)` tuple per active user. Negligible for any realistic user count.
