# Deferred Work

## Deferred from: code review of 1-2-refund-endpoint-and-tests (2026-05-19)

- **W1 — `datetime.utcnow()` deprecated (Python 3.12+):** `routes/orders.py:134,138` and `models.py` use `datetime.utcnow()`. Pre-existing codebase pattern. Should migrate to `datetime.now(timezone.utc)` in a dedicated cleanup pass.
- **W2 — No optimistic lock on refund write:** The read-check-write sequence in `refund_order` is not atomic. `SELECT FOR UPDATE` or a version counter would prevent a double-refund under concurrent requests. SQLite in-process makes this safe today; revisit if moving to Postgres or multi-worker deployment.
- **W3 — `isoformat()` produces no timezone suffix:** `refunded_at.isoformat()` yields `"2026-05-19T14:32:00"` (no `Z`/`+00:00`). RFC 3339 clients may misparse. Pre-existing — `created_at` uses `strftime` without tz too. Fix alongside W1.
- **W4 — Two `datetime.utcnow()` calls in `refund_order` not derived from same instant:** Expiry check (line 134) and `refunded_at` assignment (line 138) call `datetime.utcnow()` independently. At extreme boundary (order aged within microseconds of 30 days) these could theoretically disagree. Negligible in practice; capture one `now = datetime.utcnow()` and reuse.
