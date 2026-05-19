# Quickstart: Order Refund

End-to-end walkthrough an operator can run by hand against a fresh
checkout to confirm the feature works.

## Prerequisites

- Repo checked out at `001-order-refund`.
- Dependencies installed: `pip install -e ".[dev]"`.
- `app.db` deleted (or absent) — schema is created at startup from
  `Base.metadata` and there are no migrations.

## Run the service

```bash
uvicorn api.main:app --reload --app-dir src
```

## Walk the happy path

```bash
# 1. Create a user.
curl -s -X POST http://localhost:8000/users \
  -H 'content-type: application/json' \
  -d '{"email":"alice@example.com","name":"Alice"}'
# → {"id": 1, ...}

# 2. Create an order owned by that user.
curl -s -X POST http://localhost:8000/orders \
  -H 'content-type: application/json' \
  -H 'X-User-Id: 1' \
  -d '{"items":[{"sku":"abc","quantity":2,"unit_price":9.99}]}'
# → {"id": 1, "total": 1998, ...}

# 3. Refund it.
curl -s -X POST http://localhost:8000/orders/1/refund \
  -H 'X-User-Id: 1'
# → 201 {"id": 1, "order_id": 1, "amount": 1998, "created_at": "..."}
```

## Walk the error paths

```bash
# A. Not authenticated — no X-User-Id header → 401.
curl -i -X POST http://localhost:8000/orders/1/refund

# B. Not your order — user 2 tries to refund user 1's order → 404
#    (identical response to "order does not exist").
curl -s -X POST http://localhost:8000/users \
  -H 'content-type: application/json' \
  -d '{"email":"bob@example.com","name":"Bob"}'
curl -i -X POST http://localhost:8000/orders/1/refund -H 'X-User-Id: 2'
curl -i -X POST http://localhost:8000/orders/9999/refund -H 'X-User-Id: 1'

# C. Already refunded — retry the successful refund from step 3 → 409.
curl -i -X POST http://localhost:8000/orders/1/refund -H 'X-User-Id: 1'

# D. Window expired — requires backdating an order's created_at in the
#    DB (no API to do this). See test_refunds.py for the in-test
#    equivalent.
```

## Run the tests

```bash
pytest tests/test_refunds.py -v
```

Expected: happy-path test + one test per FR-008 failure mode all pass.
