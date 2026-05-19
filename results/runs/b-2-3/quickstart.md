# Quickstart: Order Refund

**Feature**: `001-order-refund`
**Date**: 2026-05-19

---

## Prerequisites

- Service running locally (`uvicorn src.api.main:app --reload`)
- A user and at least one order created (see examples below)

---

## 1. Create a user

```bash
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "name": "Alice"}' | python3 -m json.tool
# Note the returned "id" — use it as X-User-Id below
```

## 2. Create an order

```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items": [{"sku": "WIDGET-1", "quantity": 2, "unit_price": 9.99}]}' \
  | python3 -m json.tool
# Note the returned "id" — use it as order_id below
```

## 3. Request a refund

```bash
curl -s -X POST http://localhost:8000/orders/1/refund \
  -H "X-User-Id: 1" | python3 -m json.tool
```

**Expected success response (HTTP 200)**:

```json
{
  "order_id": 1,
  "refunded": true,
  "refunded_at": "2026-19-05"
}
```

## 4. Verify error cases

**Missing auth (401)**:
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/orders/1/refund
# → 401
```

**Already refunded (422)**:
```bash
curl -s -X POST http://localhost:8000/orders/1/refund -H "X-User-Id: 1"
# → 422 {"detail": "order has already been refunded"}
```

**Order not found (404)**:
```bash
curl -s -X POST http://localhost:8000/orders/9999/refund -H "X-User-Id: 1"
# → 404 {"detail": "order not found"}
```

---

## 5. Run the tests

```bash
pytest tests/test_orders.py -v
```

All refund-related tests are in `tests/test_orders.py` and use the in-memory
SQLite fixture — no running server needed.
