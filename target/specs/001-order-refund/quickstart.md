# Quickstart: Order Refund

How to exercise the new endpoint locally once it's implemented.

## Run the service

```bash
uvicorn api.main:app --reload
```

The first request triggers `Base.metadata.create_all`, which now
includes the `refunds` table and the new `Order.refunded_at` column.
If you have an existing `app.db` from before this feature, delete it
first (per CLAUDE.md, the operator wipes `app.db` between schema
changes).

## Create a user and an order

```bash
curl -s -X POST http://localhost:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","name":"Alice"}'
# → { "id": 1, ... }

curl -s -X POST http://localhost:8000/orders \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: 1' \
  -d '{"items":[{"sku":"WIDGET","quantity":2,"unit_price":9.99}]}'
# → { "id": 1, "user_id": 1, "total": 1998, ... }
```

## Refund the order (happy path)

```bash
curl -s -X POST http://localhost:8000/orders/1/refund \
  -H 'X-User-Id: 1'
# → 201
# {
#   "id": 1,
#   "order_id": 1,
#   "amount": 1998,
#   "created_at": "2026-05-19T12:34:56"
# }
```

A subsequent `GET /orders/1` will still succeed; the refunded state is
visible through the `refunded_at` column on the order row (the existing
`OrderOut` response does not expose it — that is fine; the refund
record is the canonical confirmation that the spec requires us to
return).

## Rejection paths to verify manually

| Scenario | Command | Expected |
|----------|---------|----------|
| Unauthenticated | `curl -i -X POST http://localhost:8000/orders/1/refund` | 401 |
| Order does not exist | `curl -i -X POST http://localhost:8000/orders/999/refund -H 'X-User-Id: 1'` | 404 |
| Order owned by another user | Create user 2 (`POST /users`), then `curl -i -X POST http://localhost:8000/orders/1/refund -H 'X-User-Id: 2'` | 404 (deliberately not 403) |
| Already refunded | Repeat the happy-path command | 409 |
| Outside 30-day window | Requires a pre-aged order; cover this case with the automated test instead (see `tests/test_refunds.py`). | 400 |

## Run the test suite

```bash
pytest tests/test_refunds.py -q
```

The tests cover the happy path and each rejection path above, including
the 30-day boundary case (which is the only one that's awkward to
reproduce manually).
