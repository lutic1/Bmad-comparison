# Fix order date formatting bug

## Context
The `created_at` field in order API responses is formatted with `"%Y-%d-%m"` (YYYY-DAY-MONTH), which swaps day and month. The correct ISO 8601 format is `"%Y-%m-%d"` (YYYY-MONTH-DAY). The bug exists in three places in the production code, and the unit tests have been written to match the incorrect output, so they also need updating.

## Changes

### 1. `src/api/utils/dates.py` — line 5
```python
# Before
return dt.strftime("%Y-%d-%m")
# After
return dt.strftime("%Y-%m-%d")
```

### 2. `src/api/routes/orders.py` — lines 77, 101, 127
Fix `"%Y-%d-%m"` → `"%Y-%m-%d"` in all three occurrences:
- `create_order()` line 77
- `get_order()` line 101
- `_format_created_at()` line 127

### 3. `tests/test_dates.py` — lines 8, 13
Update expected values to match corrected format:
- `"2025-07-03"` → `"2025-03-07"` (March 7 = month 03, day 07)
- `"2024-31-12"` → `"2024-12-31"` (December 31)

## Verification
Run `pytest tests/test_dates.py` — both tests should pass with the corrected expectations.
