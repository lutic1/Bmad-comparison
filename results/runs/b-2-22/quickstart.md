# Quickstart — Order Refund

How to exercise the feature once implemented.

## Local run

```bash
# from repo root
pytest tests/test_refunds.py -v
```

Tests use the in-memory SQLite + `client` fixture in `tests/conftest.py`,
so no DB setup is required.

## Manual smoke (against a running app)

```bash
# Start the service
uvicorn api.main:app --reload

# Create a user
curl -s -X POST localhost:8000/users \
  -H 'content-type: application/json' \
  -d '{"email":"a@example.com","name":"Alice"}'

# Create an order as that user (suppose the user got id 1)
curl -s -X POST localhost:8000/orders \
  -H 'content-type: application/json' \
  -H 'X-User-Id: 1' \
  -d '{"items":[{"sku":"sku-1","quantity":1,"unit_price":12.99}]}'

# Refund that order (suppose order id 1)
curl -s -X POST localhost:8000/orders/1/refund -H 'X-User-Id: 1'
# → 201
# {
#   "id": 1,
#   "order_id": 1,
#   "amount": 1299,
#   "created_at": "2026-05-19T14:23:01.234567"
# }

# Try to refund again
curl -s -X POST localhost:8000/orders/1/refund -H 'X-User-Id: 1'
# → 409 {"detail":"order already refunded"}

# Try without auth
curl -s -X POST localhost:8000/orders/1/refund
# → 401 {"detail":"missing X-User-Id header"}
```

## Acceptance verification

Map back to spec Success Criteria:

- **SC-001** (eligible owner can refund): happy-path test in `tests/test_refunds.py`.
- **SC-002** (all rejection paths return clear errors): five error-path tests.
- **SC-003** (refunded order remains refunded on subsequent reads):
  happy-path test issues a follow-up `GET /orders/{id}` and asserts the
  order's refunded state — *or* asserts `Order.refunded_at is not None`
  via the DB session, depending on whether `OrderOut` is extended to
  surface `refunded_at` (out of scope for this feature; the spec only
  requires that the refunded state is persistent, which the
  happy-path test confirms by re-fetching the `Refund` row).
- **SC-004** (test coverage): six tests in one file, all green via `pytest`.
