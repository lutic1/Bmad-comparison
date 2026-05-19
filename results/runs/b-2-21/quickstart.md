# Quickstart — Order Refund

This is the manual smoke test for the new endpoint, runnable against a
local dev instance of the service. Automated coverage lives in
`tests/test_refunds.py`.

## Prereqs

- The service is runnable per the repo's existing instructions.
- `app.db` may be wiped between runs (per project convention) — that's
  fine; the steps below create everything they need.

## Steps

1. Start the service.

2. Create a user.

   ```bash
   curl -s -X POST http://localhost:8000/users \
     -H "content-type: application/json" \
     -d '{"email":"alice@example.com","name":"Alice"}'
   ```

   Note the returned `id` (call it `U1`).

3. Create an order for that user.

   ```bash
   curl -s -X POST http://localhost:8000/orders \
     -H "content-type: application/json" \
     -H "X-User-Id: U1" \
     -d '{"items":[{"sku":"ABC","quantity":1,"unit_price":12.50}]}'
   ```

   Note the returned `id` (call it `O1`).

4. **Happy path** — refund the order.

   ```bash
   curl -i -X POST http://localhost:8000/orders/O1/refund \
     -H "X-User-Id: U1"
   ```

   Expect `201` and a JSON body shaped like
   `{"id": ..., "order_id": O1, "amount": 1250, "created_at": "..."}`.

5. **Already refunded** — repeat step 4.

   Expect `409` with `{"detail": "order already refunded"}`.

6. **Not owned** — create a second user `U2`, then attempt to refund
   `O1` as `U2`.

   Expect `403` with `{"detail": "forbidden"}`.

7. **Not found** — refund a non-existent order id.

   ```bash
   curl -i -X POST http://localhost:8000/orders/999999/refund \
     -H "X-User-Id: U1"
   ```

   Expect `404` with `{"detail": "order not found"}`.

8. **Unauthenticated** — refund without the header.

   ```bash
   curl -i -X POST http://localhost:8000/orders/O1/refund
   ```

   Expect `401`.

9. **Outside window** — can't be exercised purely over HTTP (no way to
   backdate via the API). Covered by `tests/test_refunds.py`, which
   seeds an order with `created_at` set to 31 days ago and asserts the
   `400` response.

## Done

All five rejection paths plus the happy path return as documented.
