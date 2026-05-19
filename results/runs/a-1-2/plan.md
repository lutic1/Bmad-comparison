# Fix: Order Date Formatting Bug

## Context
The `strftime` format string `"%Y-%d-%m"` swaps day and month, producing YYYY-DD-MM instead of the standard ISO 8601 YYYY-MM-DD. This affects all `created_at` values returned by order endpoints. The tests currently assert the wrong (swapped) output and must be corrected too.

## Root Cause
The format specifier `%d` (day) and `%m` (month) are in the wrong order everywhere the format string appears.

## Changes

### 1. `src/api/utils/dates.py` — line 5
```python
# Before
return dt.strftime("%Y-%d-%m")
# After
return dt.strftime("%Y-%m-%d")
```

### 2. `src/api/routes/orders.py` — lines 77, 101, 127
All three occurrences of `strftime("%Y-%d-%m")` → `strftime("%Y-%m-%d")`.

### 3. `tests/test_dates.py` — lines 8, 13
Update expected values to match correct ISO 8601 output:
- `"2025-07-03"` → `"2025-03-07"`
- `"2024-31-12"` → `"2024-12-31"`

## Verification
Run `pytest tests/test_dates.py` — both tests should pass with the corrected assertions. Also run the full suite with `pytest` to confirm no regressions.
