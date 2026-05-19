# Task 2 — Medium

## Prompt (paste verbatim to the agent)

Add a `POST /orders/{order_id}/refund` endpoint. It should:

- require authentication,
- validate the order exists and belongs to the requesting user,
- only allow refunds within 30 days of order creation,
- mark the order as refunded (add a field if needed),
- and return the refund record.

Include tests.

## Acceptance criteria

- A new route `POST /orders/{order_id}/refund` exists and is wired into the FastAPI app.
- Without an `X-User-Id` header the endpoint returns `401`.
- With a different user's `X-User-Id` the endpoint returns `403` or `404` (either is acceptable as long as it doesn't leak).
- An order created more than 30 days ago returns a `400` (or `409` / `422`, but **not** a `5xx`) with a clear error message; an order created within 30 days succeeds.
- After a successful refund, fetching the order surfaces its refunded state somehow (new field on `Order`, a separate `Refund` row, or both — the agent's call).
- A second refund attempt on an already-refunded order returns a non-`5xx` error.
- The response body is a refund record (at minimum: `order_id`, refunded amount in cents, a timestamp).
- New tests cover: happy path, unauthenticated, wrong user, over-30-days, double refund. `pytest` passes.
- No new third-party dependencies beyond what's in `pyproject.toml`.

## What this probes

Well-specified, medium-sized greenfield work. Every workflow should be able
to do this. The interesting comparison is **cost** and **how much
incidental scope creep** (new admin routes, refactors of unrelated code,
"while we're here" cleanups) shows up in the diff.
