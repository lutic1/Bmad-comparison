# Task 1 — Trivial

## Prompt (paste verbatim to the agent)

There's a bug in how order dates are formatted in the API response. Find it and fix it. Update tests as needed.

## Acceptance criteria

- `api.utils.dates.format_order_date(datetime(2025, 3, 7))` returns `"2025-03-07"`.
- The `created_at` field in every `OrderOut` response uses ISO `YYYY-MM-DD` (the inlined `strftime("%Y-%d-%m")` calls in `routes/orders.py` are gone or replaced with the helper).
- `pytest` passes — the tests in `tests/test_dates.py` are updated to assert the correct format. Tests that previously locked in the wrong format must be changed.
- No unrelated refactors: the diff should touch `utils/dates.py`, `routes/orders.py`, and `tests/test_dates.py` at minimum, and ideally nothing else.

## What this probes

The smallest possible bug-fix task. If a workflow makes a meal of this — long
plans, multiple personas debating it — that's the cost it has to pay back on
the harder tasks to justify itself.
