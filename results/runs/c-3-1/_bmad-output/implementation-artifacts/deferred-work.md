# Deferred Work

## Deferred from: code review of 1-1-api-rate-limiting (2026-05-18)

- `_store` unbounded memory growth: expired entries never evicted from module-level dict; resets only on restart. Fine for v1/single-instance; add LRU eviction or TTL sweep if service runs long-lived with many distinct clients.
- fail-open is completely silent: `except Exception: return` logs nothing. When the rate limiter silently fails open, operators have no signal. Add a log line (e.g. `logging.warning(...)`) in v2 when observability hooks are added (deferred per PRD §5).
- Invalid env var values not validated: `RATE_LIMIT_REQUESTS=0` or negative makes every request 429; `RATE_LIMIT_WINDOW_SECONDS=0` disables windowing. Add startup validation (raise on nonsensical values) alongside any future config module.
- Import ordering: `from api.rate_limit import check_rate_limit` placed between third-party imports in `orders.py` and `users.py` instead of with local imports (`from api.deps`, `from api.models`). Fix by adding ruff/isort to the project rather than manual reordering.
