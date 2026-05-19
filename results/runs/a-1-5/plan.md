# Fix order date format bug

## Context

`OrderOut.created_at` is returned as a string formatted with `strftime("%Y-%d-%m")`. The format string is wrong: `%d` is day-of-month and `%m` is month-of-year, so the output is `Year-Day-Month` instead of the ISO 8601 `Year-Month-Day`. For dates where the day is ≤ 12 this looks superficially valid but means the wrong calendar date (March 7 renders as `2025-07-03`); for days > 12 the result is not a valid ISO date at all (Dec 31 → `2024-31-12`).

The existing unit tests in `tests/test_dates.py` were written against the buggy output, so they currently codify the bug rather than catch it. They need to be corrected as part of the fix.

## The fix

Replace `"%Y-%d-%m"` with `"%Y-%m-%d"` in every occurrence, and update the two tests to assert the correct ISO output.

### Files to change

1. **`src/api/routes/orders.py`** — three occurrences of `strftime("%Y-%d-%m")`:
   - Line 77 (inside `create_order`'s `OrderOut(...)` construction)
   - Line 101 (inside `get_order`'s `OrderOut(...)` construction)
   - Line 127 (inside `_format_created_at`, currently unused but has the same bug — fix the format string; do not delete the function, per "no unrelated refactors")

2. **`src/api/utils/dates.py`** — line 5, `format_order_date`: same `strftime("%Y-%d-%m")` → `"%Y-%m-%d"`.

3. **`tests/test_dates.py`** — correct the two assertions that codify the bug:
   - Line 8: `"2025-07-03"` → `"2025-03-07"` (datetime(2025, 3, 7) is March 7).
   - Line 13: `"2024-31-12"` → `"2024-12-31"` (datetime(2024, 12, 31) is Dec 31).

No new tests are strictly needed — the corrected unit tests already cover both a "low day number" case (where the bug silently produces a valid-but-wrong date) and an "end of year" case (where the bug produces an invalid date). Together they pin the format down.

## Verification

From `/Users/luisticas/bmad-demo/target`:

```
pytest tests/test_dates.py -q
pytest -q
```

Both should pass. The full suite is worth running because order endpoints round-trip `created_at` through the response model — if any other test inspected the field, it would surface here.
