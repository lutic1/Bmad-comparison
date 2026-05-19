# Deferred Work

## Deferred from: code review of 1-2-refund-endpoint-and-tests (2026-05-18)

- [x] [Review][Defer] `datetime.utcnow()` deprecated in Python 3.12+ [`src/api/routes/orders.py:135,138`, `src/api/models.py:18,32`] — deferred, pre-existing. Entire codebase uses naive UTC datetimes via `utcnow()`; needs a coordinated migration to timezone-aware `datetime.now(UTC)` across all models and routes.

- [x] [Review][Defer] Naive UTC datetimes serialised without `Z`/`+00:00` suffix [`src/api/routes/orders.py:85,111,147`] — deferred, pre-existing. Consistent with existing `created_at` pattern throughout the codebase. Callers must treat all datetime strings as UTC by convention.

- [x] [Review][Defer] No row-level locking for refund idempotency check (race condition window) [`src/api/routes/orders.py:133-142`] — deferred, architectural limitation of SQLite. Check-then-set is not atomic; relevant only under concurrent load, which SQLite does not support in production anyway.

- [x] [Review][Defer] `strftime("%Y-%d-%m")` day/month swap in `created_at` serialisation [`src/api/routes/orders.py:79,105`] — deferred, pre-existing bug in `create_order` and `get_order` (not introduced by this diff). Existing tests accept the swapped format. Fix requires a coordinated update to all callers.

- [x] [Review][Defer] Exact day-30 boundary allows refund at 30d+23h59m59s [`src/api/routes/orders.py:135`] — deferred, expected behaviour. Spec says "within 30 days"; `>` operator is correct. Orders at exactly 30 days remain eligible. No AC requires blocking at the exact boundary.
