# Implementation Plan: Order Refund

**Branch**: `001-order-refund` | **Date**: 2026-05-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-order-refund/spec.md`

## Summary

Add `POST /orders/{order_id}/refund` to the existing FastAPI orders router. The endpoint authenticates the caller via the existing `X-User-Id` header dependency, validates order ownership, enforces a 30-day refund window (inclusive), marks the order as refunded by setting two new columns on the `Order` model (`refunded`, `refunded_at`), and returns a `RefundOut` record with the order ID, refund timestamp, and amount in cents.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (declarative `Mapped[...]`), Pydantic v2

**Storage**: SQLite via SQLAlchemy — two new columns added to `orders` table; schema recreated at startup, no migrations

**Testing**: pytest with the existing `client` fixture in `tests/conftest.py` (in-memory SQLite per test)

**Target Platform**: Linux server (web service)

**Project Type**: web-service

**Performance Goals**: Standard synchronous web service latency; no throughput requirement specified

**Constraints**: No new third-party dependencies; synchronous local processing only

**Scale/Scope**: Single additive endpoint; two new `Order` columns; one new Pydantic model; one new test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest | ✅ PASS | No new dependencies introduced |
| Idiomatic FastAPI: small route functions, Pydantic models, Depends | ✅ PASS | Route mirrors existing `get_order` / `create_order` pattern |
| Tests non-optional (≥80% coverage, happy-path + error-path) | ✅ PASS | `tests/test_refund.py` covers all 6 acceptance scenarios |
| Conventional commits | ✅ PASS | Authoring responsibility; no code gate |
| No new third-party dependencies without justification | ✅ PASS | Only stdlib `datetime` used |
| Type hints on all public functions and route handlers | ✅ PASS | Enforced in implementation tasks |
| Don't refactor unrelated code | ✅ PASS | Touch only `models.py` (+2 fields) and `routes/orders.py` (+1 route, +2 Pydantic models) |

**Post-design re-check**: ✅ All gates pass after Phase 1 design.

## Project Structure

### Documentation (this feature)

```text
specs/001-order-refund/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── refund-endpoint.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/
└── api/
    ├── models.py          # Add refunded: bool, refunded_at: datetime | None to Order
    └── routes/
        └── orders.py      # Add RefundOut Pydantic model + POST /orders/{order_id}/refund

tests/
└── test_refund.py         # New: all 6 acceptance scenarios
```

**Structure Decision**: Single-project layout matching the existing repo. All changes are additive within the existing `src/api/` tree. No new modules, packages, or services introduced.
