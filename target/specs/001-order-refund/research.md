# Research: Order Refund

**Feature**: `001-order-refund`
**Date**: 2026-05-19
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## Decision 1: Storage — no separate Refund table

**Decision**: Add two columns directly to the existing `orders` table: `refunded`
(bool, default False) and `refunded_at` (datetime, nullable).

**Rationale**: The spec explicitly states "The refund record does not require a
separate persistent entity — it is derived from the updated order record."  A
separate table would add a join for every refund lookup with no benefit at this
scope.

**Alternatives considered**: A dedicated `refunds` table — rejected because it
adds a model, a relationship, and a join for a single-call-site feature.

---

## Decision 2: 30-day window boundary

**Decision**: The window is inclusive. An order created exactly 30 * 24 * 60 * 60
seconds before the request is still eligible. Implementation:
`datetime.utcnow() - order.created_at <= timedelta(days=30)`.

**Rationale**: The spec acceptance scenario 2 (US1) states the 30-day boundary is
inclusive. Using `timedelta(days=30)` with `<=` satisfies this.

**Alternatives considered**: Exclusive boundary (`<`) — rejected because the spec
is explicit.

---

## Decision 3: Ownership — return 404 for wrong owner

**Decision**: If an order exists but belongs to a different user, return 404 (not
403). The spec requires this to prevent ownership disclosure (FR-003).

**Rationale**: FR-003: "orders owned by other users MUST be treated as not found."
Note: the existing `GET /orders/{order_id}` returns 403 for wrong owner — this
feature intentionally diverges from that existing behavior because the spec is
authoritative. The existing route is not changed.

**Alternatives considered**: Return 403 to match existing pattern — rejected
because the spec explicitly prohibits ownership disclosure.

---

## Decision 4: Error response codes

| Condition                  | HTTP Status | Detail                          |
|----------------------------|-------------|---------------------------------|
| Missing X-User-Id header   | 401         | "missing X-User-Id header"      |
| Unknown user               | 401         | "unknown user"                  |
| Order not found            | 404         | "order not found"               |
| Order owned by other user  | 404         | "order not found"               |
| Past 30-day window         | 422         | "refund window has expired"     |
| Already refunded           | 422         | "order has already been refunded" |

**Rationale**: 401 for auth failures (reuses existing dependency behaviour). 404
for not-found/ownership (FR-003). 422 (Unprocessable Entity) for business rule
violations — same convention FastAPI uses for validation errors, appropriate here
since the request is structurally valid but violates domain rules.

---

## Decision 5: Route placement

**Decision**: Add the endpoint to `src/api/routes/orders.py` on the existing
`router` instance.

**Rationale**: Refund is an action on an order. The existing file already owns all
order-related routes. No new file or router needed.

---

## Decision 6: Response shape

**Decision**: `RefundOut` Pydantic model with fields: `order_id: int`,
`refunded: bool`, `refunded_at: str`. Date formatted with `_format_created_at`
(same helper used by `OrderOut`).

**Rationale**: Matches the existing response pattern in the codebase (dates as
formatted strings, not raw datetimes). Keeps the `RefundOut` minimal — only what
the spec requires (FR-007).
