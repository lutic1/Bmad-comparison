# Data Model: API Rate Limiting

**Feature**: 001-api-rate-limiting
**Date**: 2026-05-19

## Overview

Rate limit state is held entirely in-memory. There are no new database
tables or SQLAlchemy models. The state is discarded on service restart
(per spec assumption).

## In-Memory State: RateLimitStore

```
RateLimitStore
├── _lock: threading.Lock
│     Serialises all read-modify-write operations on _store.
└── _store: dict[str, RateLimitEntry]
      Keyed by client identity string.
```

### RateLimitEntry (value type)

| Field        | Type  | Description                                              |
|--------------|-------|----------------------------------------------------------|
| count        | int   | Number of requests made in the current window            |
| window_start | float | Unix timestamp (time.time()) when the current window began |

The entry is stored as a plain tuple `(count, window_start)` to keep it
lightweight. No ORM mapping.

## Client Identity Key

| Client type        | Key format       | Example           |
|--------------------|------------------|-------------------|
| Authenticated      | `"{user_id}"`    | `"42"`            |
| Unauthenticated    | `"ip:{address}"` | `"ip:10.0.0.1"`   |

Namespacing prevents collisions between integer user IDs and IP strings.

## Configuration Values (not persisted)

| Name                        | Default | Source                            |
|-----------------------------|---------|-----------------------------------|
| `RATE_LIMIT_REQUESTS`       | 60      | `os.environ` or module constant   |
| `RATE_LIMIT_WINDOW_SECONDS` | 60      | `os.environ` or module constant   |

## State Transitions

```
Request arrives
      │
      ▼
Extract client key
      │
      ▼
Load entry from store (or create fresh entry)
      │
      ├─[window expired]──► reset count to 0, update window_start
      │
      ▼
count < limit?
      │
      ├─[yes]──► increment count, save entry, allow request, add headers
      │
      └─[no]───► return 429, add headers + Retry-After, do NOT increment
```

## Files Affected

| Path                              | Change    |
|-----------------------------------|-----------|
| `src/api/middleware/__init__.py`  | New (empty)|
| `src/api/middleware/rate_limit.py`| New       |
| `src/api/main.py`                 | Modified (register middleware) |
| `tests/test_rate_limit.py`        | New       |
