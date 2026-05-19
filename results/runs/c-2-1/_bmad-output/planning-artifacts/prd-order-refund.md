# PRD — Order Refund Endpoint

**Status:** Draft  
**Author:** John (PM)  
**Date:** 2026-05-18  
**Stack context:** FastAPI · SQLAlchemy 2.x · SQLite · Pydantic v2 · pytest

---

## 1. Problem Statement

Users have no way to request a refund through the API. Once an order is created it is immutable and permanent. The service needs a first-class refund operation that enforces business rules (ownership, time window) and returns a structured refund record — without requiring a payment processor integration at this stage.

---

## 2. Goals

| # | Goal |
|---|------|
| G1 | Expose `POST /orders/{order_id}/refund` so a caller can initiate a refund on their own order. |
| G2 | Enforce authentication: the endpoint must reject unauthenticated calls. |
| G3 | Enforce ownership: a user may only refund their own orders; attempting to refund another user's order must return 403. |
| G4 | Enforce the 30-day refund window: orders created more than 30 days ago must be rejected with a clear error. |
| G5 | Mark the order as refunded so subsequent reads reflect the new state. |
| G6 | Return a structured refund record on success. |
| G7 | Ship with tests that cover the golden path and each rejection case. |

---

## 3. Non-Goals

| # | Non-Goal |
|---|----------|
| NG1 | **No payment processor integration.** Refunds are a state change only; actual money movement is out of scope. |
| NG2 | **No partial refunds.** This release handles full-order refunds only. |
| NG3 | **No refund cancellation or reversal.** Once refunded, the state is final within this service. |
| NG4 | **No async processing, webhooks, or event emission.** |
| NG5 | **No admin override.** There is no privileged user role that bypasses ownership or time-window rules. |
| NG6 | **No database migrations.** Schema is recreated from `Base.metadata`; operators wipe `app.db` on deploy. |
| NG7 | **No change to the money storage convention.** `total` remains in integer cents. |

---

## 4. Functional Requirements

### FR-1 — Authentication
The endpoint depends on the existing `get_current_user` dependency (via `X-User-Id` header). A missing or unknown user returns **401**.

### FR-2 — Order existence
If `order_id` does not exist in the database, return **404**.

### FR-3 — Ownership check
If the order's `user_id` does not match the authenticated user, return **403**.

### FR-4 — Idempotency / double-refund guard
If the order is already marked as refunded, return **409 Conflict** — do not re-process.

### FR-5 — 30-day window
Compare `order.created_at` (UTC) with `datetime.utcnow()`. If the delta exceeds 30 days, return **422 Unprocessable Entity** with a descriptive message.

### FR-6 — State mutation
Set `order.refunded = True` and `order.refunded_at = <utcnow>` on the Order row. (New columns — see Schema Changes.)

### FR-7 — Response shape
On success return **200 OK** with a JSON body:

```json
{
  "order_id": 42,
  "refunded": true,
  "refunded_at": "2026-05-18T14:30:00",
  "total": 1998
}
```

Field meanings:
- `order_id` — the order that was refunded
- `refunded` — always `true` on a 200 response
- `refunded_at` — UTC timestamp of the refund
- `total` — the refunded amount in cents (same as `order.total`)

---

## 5. Schema Changes

Add two columns to the `orders` table:

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `refunded` | Boolean | No | `False` | Flag; drives idempotency check |
| `refunded_at` | DateTime | Yes | `NULL` | Set only when refund is processed |

No migration needed per project convention — schema is rebuilt on startup.

---

## 6. Acceptance Criteria

| ID | Scenario | Expected result |
|----|----------|----------------|
| AC-01 | `POST /orders/{id}/refund` without `X-User-Id` header | `401` |
| AC-02 | `POST /orders/{id}/refund` with unknown user id | `401` |
| AC-03 | `POST /orders/9999/refund` where order does not exist | `404` |
| AC-04 | User A tries to refund User B's order | `403` |
| AC-05 | Order created 31+ days ago; valid owner requests refund | `422` with explanatory message |
| AC-06 | Valid owner refunds an eligible order | `200` with refund record; `order.refunded == True` persisted |
| AC-07 | Same owner calls the endpoint a second time on already-refunded order | `409` |
| AC-08 | `GET /orders/{id}` after a successful refund reflects `refunded: true` and `refunded_at` | `200` with updated fields |
| AC-09 | Tests pass with `pytest` — zero failures | CI green |

---

## 7. Error Response Conventions

Follow the pattern already used in the repo (`{"detail": "<message>"}`):

| Condition | HTTP status | `detail` example |
|-----------|-------------|-----------------|
| No / bad auth | 401 | `"Not authenticated"` |
| Order not found | 404 | `"Order not found"` |
| Wrong owner | 403 | `"Forbidden"` |
| Already refunded | 409 | `"Order has already been refunded"` |
| Outside window | 422 | `"Refund window of 30 days has expired"` |

---

## 8. Open Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| OQ-1 | Should `GET /orders/{order_id}` response also expose `refunded` and `refunded_at`? The AC-08 criterion assumes yes, but the existing response schema (`OrderResponse`) would need to grow two fields. | Low — additive, backwards-compatible | Architect / Dev |
| OQ-2 | Is 30 days calculated as calendar days (midnight-to-midnight) or elapsed seconds (2592000 s)? The simpler `timedelta(days=30)` comparison against UTC datetimes is assumed here. | Edge-case correctness at day 30 boundary | PM to confirm |
| OQ-3 | Should a refunded order still be retrievable via `GET /orders/{order_id}`? Currently assumed yes — it remains visible, just flagged. | UX / audit trail | Stakeholder |
| OQ-4 | `total` is stored as integer cents. The refund record echoes this. Is there a display-layer expectation (e.g. dollars with decimal) that should influence the response contract? | API contract | Frontend consumer |
| OQ-5 | Are there downstream systems (analytics, fulfilment) that need to be notified of refund state changes? If so, a future event-emission story will be needed. | Scope creep risk | PM / Architect |

---

## 9. Out-of-Scope (explicitly deferred)

- Email/notification to user on refund
- Refund reason / notes field
- Admin audit log
- Bulk refund operations
- Currency / locale handling

---

## 10. Success Metrics (post-ship)

- All 9 acceptance criteria pass in CI.
- Zero 500 errors on any of the defined AC scenarios in integration testing.
- No regression in existing `test_orders.py`, `test_users.py`, or `test_dates.py`.
