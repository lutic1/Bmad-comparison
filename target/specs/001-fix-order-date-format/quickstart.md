# Quickstart: Validating the Date Format Fix

**Feature**: 001-fix-order-date-format

## Prerequisites

```bash
cd /path/to/repo
pip install -e ".[dev]"   # or however deps are installed
```

## Run the test suite

```bash
pytest tests/test_orders.py -v
```

All five existing tests plus the new `created_at` format assertions must pass.

## Manual smoke test

```bash
# Start the server
uvicorn api.main:app --reload

# Create a user
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test"}' | python3 -m json.tool

# Create an order (replace 1 with actual user id)
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items": [{"sku": "WIDGET", "quantity": 1, "unit_price": 9.99}]}' \
  | python3 -m json.tool
```

**Expected**: `created_at` in the response is `"YYYY-MM-DD"` (e.g. `"2026-05-19"`).
**Buggy output** (before fix): `"2026-19-05"` — day and month are swapped.

## Validation checklist

- [ ] `created_at` matches pattern `^\d{4}-\d{2}-\d{2}$`
- [ ] Month value is 01–12 (not a day value like 19 in the month position)
- [ ] `pytest tests/test_orders.py` exits 0 with no failures
