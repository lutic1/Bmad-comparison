# Fix: Order Date Formatting Bug

## Context

The `strftime` format string `"%Y-%d-%m"` produces **year-day-month** order (e.g., March 7 → `"2025-07-03"`). The correct ISO 8601 format is `"%Y-%m-%d"` (year-month-day). The bug exists in every place dates are formatted, and the existing tests encode the wrong expected values, so they pass despite the bug.

## Changes

### 1. `src/api/routes/orders.py`

Fix the format string in three places:

- **Line 77** (`create_order`): `strftime("%Y-%d-%m")` → `strftime("%Y-%m-%d")`
- **Line 101** (`get_order`): `strftime("%Y-%d-%m")` → `strftime("%Y-%m-%d")`
- **Line 127** (`_format_created_at` helper, unused but still wrong): same fix

### 2. `src/api/utils/dates.py`

- **Line 5**: `strftime("%Y-%d-%m")` → `strftime("%Y-%m-%d")`

### 3. `tests/test_dates.py`

Update the two test assertions to expect correct ISO 8601 output:

- **Line 8**: `"2025-07-03"` → `"2025-03-07"`
- **Line 13**: `"2024-31-12"` → `"2024-12-31"`

## Verification

```
cd /Users/luisticas/bmad-demo/target
pytest tests/test_dates.py tests/test_orders.py -v
```

All 7 tests (2 date unit tests + 5 order route tests) should pass.
