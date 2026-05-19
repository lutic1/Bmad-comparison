# Fix order date format in API response

## Context

The Orders API returns `created_at` as a date string, but the format
string is `"%Y-%d-%m"` — day and month are swapped. So an order created
on 7 March 2025 is returned as `"2025-07-03"` (looks like 3 July), and
an order created on 31 December 2024 is returned as `"2024-31-12"`
(invalid). Two existing date tests assert the buggy output, so the
fix needs the tests updated and a regression test on the actual API
response.

## The bug

Three places use the wrong format string `"%Y-%d-%m"`:

- `src/api/routes/orders.py:77` — `create_order` response (live)
- `src/api/routes/orders.py:101` — `get_order` response (live)
- `src/api/utils/dates.py:5` — `format_order_date` utility (used only
  by `tests/test_dates.py`; not wired into the routes)

The intent is clearly `YYYY-MM-DD` (ISO 8601 date). Fix is to swap
`%d` and `%m`.

There is also a dead helper `_format_created_at` at
`src/api/routes/orders.py:126` with the same bug. It has no callers
(grep confirms). I'll leave it alone — touching it is out of scope per
the project guardrail "don't refactor unrelated code while you're
here." Flagging here so the reviewer can decide.

## Changes

### 1. `src/api/routes/orders.py`

- Line 77: `order.created_at.strftime("%Y-%d-%m")` → `order.created_at.strftime("%Y-%m-%d")`
- Line 101: same swap

### 2. `src/api/utils/dates.py`

- Line 5: `dt.strftime("%Y-%d-%m")` → `dt.strftime("%Y-%m-%d")`

### 3. `tests/test_dates.py`

These tests pin the wrong format. Update the expected values:

- Line 8: `"2025-07-03"` → `"2025-03-07"`
- Line 13: `"2024-31-12"` → `"2024-12-31"`

### 4. `tests/test_orders.py` — add regression test

The existing order tests don't assert anything about `created_at`, so
the bug shipped undetected. Add one test that drives the API end-to-end
and asserts the response shape. Using `datetime.utcnow()` (matches the
model default) and `re.fullmatch(r"\d{4}-\d{2}-\d{2}", ...)` plus
`datetime.strptime(..., "%Y-%m-%d")` gives a tight assertion without
depending on the test's wall clock minute-by-minute.

Sketch:

```python
from datetime import datetime, timezone
import re

def test_create_order_returns_iso_date(client):
    user = _make_user(client, email="date@example.com")
    before = datetime.utcnow().date()
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    )
    after = datetime.utcnow().date()
    assert resp.status_code == 201
    created_at = resp.json()["created_at"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", created_at)
    parsed = datetime.strptime(created_at, "%Y-%m-%d").date()
    assert before <= parsed <= after
```

## Critical files

- `src/api/routes/orders.py` (edit lines 77, 101)
- `src/api/utils/dates.py` (edit line 5)
- `tests/test_dates.py` (edit lines 8, 13)
- `tests/test_orders.py` (append one test)

## Verification

From `/Users/luisticas/bmad-demo/target`:

```
pytest tests/test_dates.py tests/test_orders.py -q
```

Expected: all tests pass, including the new
`test_create_order_returns_iso_date`. Then run the full suite
(`pytest -q`) to confirm no other test was pinning the buggy format.
