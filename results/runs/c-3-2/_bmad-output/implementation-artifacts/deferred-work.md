# Deferred Work

## Deferred from: code review of 1-1-rate-limiting (2026-05-19)

- **Unbounded memory growth of `_store`** [`src/api/rate_limit.py:11`]: keys accumulate indefinitely; no eviction of stale client entries. Acceptable for v1 single-process deployment; revisit if service is long-lived with high client churn.
- **Invalid env var values (_LIMIT=0, _WINDOW=0, negatives) silently break rate limit logic** [`src/api/rate_limit.py:8-9`]: no bounds validation on `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS`. Operator documentation should warn against zero/negative values; guard with `max(1, int(...))` if stricter safety is needed.
