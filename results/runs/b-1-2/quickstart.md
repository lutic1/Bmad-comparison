# Quickstart: Verify Order Date Fix

**Feature**: 001-fix-order-date-format
**Date**: 2026-05-18

## Verify with pytest

```bash
# Run only the directly affected test file
pytest tests/test_dates.py -v

# Run the full suite to check for regressions
pytest
```

Both commands must exit 0 with no failures.

## Verify manually (dev server)

```bash
# Start the service
uvicorn src.main:app --reload

# Create a user (if needed)
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com"}' | jq .

# Create an order (replace 1 with the returned user id)
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}]}' | jq .
```

**Expected**: `created_at` in the response is `"YYYY-MM-DD"` (e.g.
`"2026-05-18"`), not `"YYYY-DD-MM"` (e.g. `"2026-18-05"`).

## What was changed

| File | Location | Change |
|------|----------|--------|
| `src/api/routes/orders.py` | line 77 | `"%Y-%d-%m"` → `"%Y-%m-%d"` |
| `src/api/routes/orders.py` | line 101 | `"%Y-%d-%m"` → `"%Y-%m-%d"` |
| `src/api/routes/orders.py` | line 127 | `"%Y-%d-%m"` → `"%Y-%m-%d"` |
| `src/api/utils/dates.py` | line 5 | `"%Y-%d-%m"` → `"%Y-%m-%d"` |
| `tests/test_dates.py` | line 8 | assertion updated to `"2025-03-07"` |
| `tests/test_dates.py` | line 13 | assertion updated to `"2024-12-31"` |
