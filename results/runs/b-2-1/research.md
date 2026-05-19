# Research: Order Refund

**Feature**: `001-order-refund`
**Date**: 2026-05-18

## Decision 1: Where to store refund state

**Decision**: Add two columns directly to the existing `Order` model — `refunded: bool` (default `False`) and `refunded_at: datetime | None` (default `None`).

**Rationale**: The spec says "mark the order as refunded (add a field if needed)". The refund state is a property of an order, not an independent entity. A separate `Refund` table would be an abstraction for a single call site, which violates the project principle against introducing abstractions for a single use. The two-column approach keeps the model flat, keeps queries trivial, and keeps the implementation small.

**Alternatives considered**:
- Separate `Refund` table with a FK to `Order`: rejected — overkill for a boolean state transition; adds a join on every read with no benefit at this scale.
- Single `status: str` enum field replacing a hypothetical future `status` column: rejected — no such column exists yet; adding a string enum field for one state is premature generalization (YAGNI).

---

## Decision 2: HTTP status for business-rule violations

**Decision**: Return `422 Unprocessable Entity` for both "refund window expired" and "order already refunded" cases.

**Rationale**: Both cases are semantically valid requests (correct auth, correct ownership, order exists) that fail a business rule. `422` is the standard REST/HTTP signal for "the server understands the request but cannot process it due to semantic errors." `409 Conflict` is a close alternative for "already refunded" but `422` is used consistently in FastAPI's own validation layer and is more appropriate for domain rule failures.

**Alternatives considered**:
- `400 Bad Request`: rejected — the request itself is well-formed; the failure is a domain rule, not a malformed input.
- `409 Conflict` for "already refunded": reasonable, but inconsistent with the "expired window" case; a single status keeps error handling uniform for API consumers.

---

## Decision 3: Request body

**Decision**: No request body. The endpoint is `POST /orders/{order_id}/refund` with no payload.

**Rationale**: There is no caller-supplied data for this operation. The order ID comes from the path, the user identity from the auth header, and the refund amount is derived from the order's existing total. Requiring an empty body would be misleading.

**Alternatives considered**:
- Accept an optional `reason` string: out of scope per spec; no requirement exists for storing a refund reason.
- Accept an explicit `amount` for partial refunds: out of scope per spec and assumptions.

---

## Decision 4: Refund timestamp source

**Decision**: Use `datetime.utcnow()` at the moment the endpoint processes the request, stored in `refunded_at`.

**Rationale**: Consistent with how `created_at` is set on `Order` and `User` in the existing codebase (both use `default=datetime.utcnow`).

**Alternatives considered**:
- `datetime.now(timezone.utc)` (timezone-aware): more correct in modern Python, but would diverge from the existing `datetime.utcnow()` pattern already used in `models.py`. Consistency with existing code takes priority here.

---

## Decision 5: Test file location

**Decision**: New file `tests/test_refund.py`.

**Rationale**: Keeps refund-specific tests discoverable and isolated. The existing test structure (implied by conftest.py) does not consolidate all route tests into one file; a dedicated file per feature follows that pattern.

**Alternatives considered**:
- Append to an existing `tests/test_orders.py`: reasonable, but that file does not exist yet; starting fresh is equivalent and cleaner.
