# Deferred Work

## Deferred from: code review of 1-1-rate-limiting (2026-05-19)

- **threading.Lock blocks async event loop** (`src/api/middleware/rate_limit.py:41`) — Sub-microsecond dict op; architecture doc justified for single-instance service. Revisit if concurrency becomes a bottleneck; replace with `asyncio.Lock` if high-traffic async usage is needed.
- **`_counters` grows without bound** (`src/api/middleware/rate_limit.py:9`) — No eviction of expired entries; benign for bounded internal user set. Revisit when horizontal scaling or high cardinality of callers is introduced (OQ-4).
- **`X-User-Id` is attacker-controlled subject key** — By design; service has no real auth. If service is ever exposed publicly, validate or authenticate the header before using it as a rate-limit key.
- **`reset()` called after teardown not before setup** (`tests/conftest.py:44`) — Pytest guarantees fixture teardown so stale-state risk is negligible. Add a pre-yield reset if test isolation concerns arise in future.
- **`RATE_LIMIT_WINDOW_SECONDS=0` disables limiting** — Setting the window to zero resets every request's own window, effectively disabling rate limiting. Add a `max(1, window)` guard if operator misconfiguration becomes a concern.
