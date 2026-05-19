# Research: Order Refund

**Feature**: `001-order-refund`
**Date**: 2026-05-19

## Decision Log

### D-001: Error code for ownership mismatch

**Decision**: Return **403 Forbidden** when the authenticated user requests a refund for an order they do not own.

**Rationale**: The existing `GET /orders/{order_id}` route already returns 403 for this case (`src/api/routes/orders.py:95`). Consistency across the API is more valuable than the marginal security gain of 404. Both responses protect against information disclosure equally at this service's scale.

**Alternatives considered**: 404 Not Found — stronger information hiding but inconsistent with the established GET endpoint pattern.

---

### D-002: Refund state model

**Decision**: Add two columns to the `orders` table: `refunded: bool` (default `False`, non-nullable) and `refunded_at: datetime | None` (nullable). No separate `refunds` table.

**Rationale**: The requirement is to "mark the order as refunded." This is a simple terminal state decoration on the existing entity. A separate table would be premature — there is no requirement for a `GET /refund` endpoint or audit history. Spec assumption explicitly defers this ("no separate Refund database table is required unless the implementer determines one is necessary").

**Alternatives considered**: Separate `refunds` table — adds JOIN complexity for no current benefit.

---

### D-003: 30-day boundary calculation

**Decision**: Eligibility check: `datetime.utcnow() - order.created_at <= timedelta(days=30)`. Boundary is inclusive.

**Rationale**: Consistent with `created_at = mapped_column(DateTime, default=datetime.utcnow)` already in the model. stdlib `timedelta(days=30)` needs no new dependencies.

**Alternatives considered**: Calendar-month calculation — overly complex; "30 days" is a fixed duration.

---

### D-004: Duplicate refund response code

**Decision**: Return **409 Conflict** when a refund is requested on an already-refunded order.

**Rationale**: 409 is the canonical HTTP status for a request that conflicts with the current resource state. Clearly distinct from input validation errors (422) and authorization failures (403/404).

**Alternatives considered**: 422 Unprocessable Entity — better suited for malformed input, not a state conflict.

---

### D-005: Concurrent request safety

**Decision**: Application-level check-then-set within a single DB transaction is sufficient. No additional locking mechanism required.

**Rationale**: SQLite serializes all writes at the database level; true concurrent write races cannot occur in this deployment. Tests use in-memory SQLite (also single-writer). Adding a UNIQUE constraint for idempotency is non-trivial in SQLite without partial indexes and is not warranted.

**Alternatives considered**: DB-level UNIQUE constraint — not cleanly supported in SQLite without partial indexes.

---

### D-006: Refund response shape

**Decision**: `RefundOut` contains `order_id: int`, `refunded_at: str` (ISO datetime), `total: int` (cents).

**Rationale**: The spec mandates "at minimum: order ID, refund timestamp, refunded status." `total` (the refunded amount) is unambiguously useful to callers and already present on the Order model at zero additional cost; omitting it would force a follow-up GET request.

**Alternatives considered**: Return full `OrderOut` — too broad; exposes items list irrelevant to a refund response. Return bare minimum three fields — forces callers to make a second GET to learn the amount.
