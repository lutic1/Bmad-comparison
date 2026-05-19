# Quickstart: Verify the Order Date Format Fix

**Feature**: `001-fix-order-date-format`
**Date**: 2026-05-18

## Reproduce the bug (before fix)

```bash
# Start the service
cd /path/to/project
uvicorn api.main:app --reload

# Create a user
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test"}' | python3 -m json.tool

# Note the returned user id, e.g. 1

# Create an order
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items": [{"sku": "WIDGET", "quantity": 1, "unit_price": 9.99}]}' \
  | python3 -m json.tool
```

Before the fix, `created_at` will show `YYYY-DD-MM` — e.g., `"2026-18-05"`
instead of `"2026-05-18"`.

---

## Verify the fix

After applying the fix, the same request should return `"2026-05-18"`.

### Run the test suite

```bash
pytest tests/test_dates.py tests/test_orders.py -v
```

All tests should pass, including:
- `test_format_order_date_basic` — asserts `"2025-03-07"`
- `test_format_order_date_end_of_year` — asserts `"2024-12-31"`
- `test_create_order_date_format` — asserts `YYYY-MM-DD` on POST
- `test_get_order_date_format` — asserts `YYYY-MM-DD` on GET

### Confirm no regressions

```bash
pytest
```
