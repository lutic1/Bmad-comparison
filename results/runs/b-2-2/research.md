# Research: Order Refund

**Date**: 2026-05-19
**Feature**: [spec.md](spec.md)

No external research required — all technology choices are dictated by the constitution and the existing codebase. Findings below document the key decisions and their rationale.

---

## Decision 1: Schema Evolution Strategy

**Decision**: Add `refunded` (boolean, default `False`) and `refunded_at` (nullable datetime) directly to the existing `Order` SQLAlchemy model.

**Rationale**: The project uses schema-from-metadata (`Base.metadata.create_all`) with no migration tooling. The CLAUDE.md explicitly states the operator wipes `app.db` between runs. Adding columns to the model is the correct and documented approach.

**Alternatives considered**:
- Separate `Refund` table — rejected; adds join complexity for a 1-to-1 relationship; the order record is the natural source of truth for its own refund state.
- Migration script — rejected; explicitly out of scope per project conventions.

---

## Decision 2: 30-Day Window Calculation

**Decision**: `datetime.utcnow() - order.created_at <= timedelta(days=30)`. An order is eligible if the delta is ≤ 30 days (i.e., exactly 30 × 86 400 seconds).

**Rationale**: Spec assumption states "30 × 24 × 60 × 60 seconds from order creation timestamp". Using `timedelta(days=30)` maps directly to this. The existing `created_at` column is stored as UTC naive datetime via `default=datetime.utcnow`.

**Alternatives considered**:
- Calendar-day comparison — rejected per spec assumption (seconds-based, not calendar).
- `<=` vs `<` boundary: spec SC-004 states "created at exactly 30 days is accepted" → use `<=`.

---

## Decision 3: HTTP Status Codes for Rejection Scenarios

**Decision**:

| Scenario | Status Code | Reason |
|----------|-------------|--------|
| Missing / invalid X-User-Id | 401 | Authentication failure (matches existing pattern) |
| Order not found or not owned by caller | 404 | Avoids disclosing order existence (FR-003) |
| Refund window expired (> 30 days) | 400 | Business rule violation — bad request |
| Order already refunded | 409 | Conflict with current resource state |

**Rationale**: 422 is reserved for Pydantic schema validation in FastAPI. Business-logic rejections use 400/409 to distinguish from schema errors. 404 for ownership violations follows the existing `get_order` route pattern.

**Alternatives considered**:
- 422 for all business errors — rejected; conflicts with FastAPI's own validation error convention.
- 403 for ownership — rejected; discloses order existence to the caller.

---

## Decision 4: Duplicate-Refund Protection

**Decision**: Check `order.refunded` flag before writing; raise 409 if already `True`. No DB-level unique constraint needed.

**Rationale**: Single-process SQLite, no concurrent writes in the deployment model. The flag check within the same request is sufficient. Adding a DB constraint would add complexity for no practical benefit at this scale.

**Alternatives considered**:
- Unique constraint on `refunded_at` — rejected; column is nullable and the flag is the canonical state indicator.

---

## Decision 5: RefundOut Response Model Placement

**Decision**: Define `RefundOut` as a Pydantic model in `src/api/routes/orders.py`, alongside the existing `OrderCreate` and `OrderOut` models that live at the top of the same file.

**Rationale**: Keeps all orders-domain Pydantic models co-located. Consistent with existing pattern where request/response models are defined in the route file.

**Alternatives considered**:
- Define in `models.py` — rejected; `models.py` contains only SQLAlchemy ORM models, not Pydantic schemas.
- Separate `schemas.py` — rejected; introduces an abstraction for a single call site (constitution Principle VII + CLAUDE.md "no abstractions for a single call site").
