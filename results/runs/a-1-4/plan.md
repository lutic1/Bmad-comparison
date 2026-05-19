# Fix order `created_at` format string

## Context

The orders API serializes `Order.created_at` with `strftime("%Y-%d-%m")`, which
emits year-day-month (e.g. `datetime(2024, 12, 31)` → `"2024-31-12"`). Callers
expect ISO 8601 (`%Y-%m-%d`). For days ≤ 12 the bug silently swaps month and
day; for days > 12 it produces an out-of-range "month" component that no date
parser will accept. The unit tests in `tests/test_dates.py` were written to
match the buggy output, so they currently lock the bug in place.

The fix: change the format string to `%Y-%m-%d` everywhere it appears, correct
the unit tests, and add a route-level regression test so a future regression
shows up in `test_orders.py` (which currently asserts nothing about the date
shape).

## Bug locations

All four use the same wrong format string `"%Y-%d-%m"`:

- `src/api/routes/orders.py:77` — `create_order` response (live bug)
- `src/api/routes/orders.py:101` — `get_order` response (live bug)
- `src/api/routes/orders.py:127` — `_format_created_at` helper (defined,
  never called — same bug, fix the string, leave the function in place to
  avoid unrelated refactor)
- `src/api/utils/dates.py:5` — `format_order_date` (only consumed by
  `tests/test_dates.py`; fix to ISO so the utility is actually correct)

## Changes

### 1. `src/api/routes/orders.py`

Replace the format string in all three sites:

- line 77: `created_at=order.created_at.strftime("%Y-%m-%d"),`
- line 101: `created_at=order.created_at.strftime("%Y-%m-%d"),`
- line 127: `return dt.strftime("%Y-%m-%d")`

### 2. `src/api/utils/dates.py`

- line 5: `return dt.strftime("%Y-%m-%d")`

### 3. `tests/test_dates.py`

Update both assertions to the corrected ISO output:

- line 8: `assert format_order_date(dt) == "2025-03-07"`
- line 13: `assert format_order_date(dt) == "2024-12-31"`

### 4. `tests/test_orders.py` — add regression test

Add a single test that creates an order, GETs it, and asserts `created_at`
matches `^\d{4}-\d{2}-\d{2}$` and round-trips through
`datetime.strptime(..., "%Y-%m-%d")`. Use the existing `client` fixture from
`tests/conftest.py` and the `X-User-Id` header pattern already used by other
tests in that file. Keep it small — one behaviour per test, per project
conventions.

## Verification

From `/Users/luisticas/bmad-demo/target`:

1. `pytest tests/test_dates.py tests/test_orders.py -q` — both files green,
   including the new regression test.
2. Manual sanity (optional): start the app, `POST /orders` with
   `X-User-Id: <existing user>`, confirm the response `created_at` is
   `YYYY-MM-DD` and matches today's UTC date.

## Out of scope

- Switching to Pydantic-native date serialization (would change the schema
  from `str` to `date`/`datetime` and ripple into clients).
- Timezone handling — `datetime.utcnow` produces naive UTC; that predates
  this bug and is not what was reported.
- Deleting the unused `_format_created_at` helper — dead-code cleanup is
  outside the scope of this bug fix per project guardrails.
