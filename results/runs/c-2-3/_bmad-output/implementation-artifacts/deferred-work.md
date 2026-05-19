# Deferred Work

## Deferred from: code review of 1-1-order-refund-endpoint (2026-05-19)

- **Race condition on concurrent refund requests** — `refund_order` checks `order.refunded` then writes it in a non-atomic sequence. Under concurrent requests both could pass the guard before either commits. Pre-existing pattern: codebase uses no DB-level locking or SELECT FOR UPDATE anywhere. Low risk on SQLite (serial writes), higher risk if DB backend changes.

- **`strftime("%Y-%d-%m")` day/month swap in `created_at` serialization** — `create_order` and `get_order` serialize `created_at` as `"%Y-%d-%m"` (e.g. `"2026-19-05"` instead of `"2026-05-19"`). Pre-existing bug, not introduced by the refund feature. New `refunded_at` field correctly uses `isoformat()`. Fix: change both sites to `strftime("%Y-%m-%d")` or `isoformat()`.
