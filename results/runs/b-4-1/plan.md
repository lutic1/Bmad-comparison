# Implementation Plan: Discount Code at Checkout

**Branch**: `001-discount-codes` | **Date**: 2026-05-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-discount-codes/spec.md`

## Summary

Add a `POST /orders/{order_id}/apply-discount` endpoint that validates a
discount code (5%, 10%, or 20%) and records it on the order. A new
`DiscountCode` SQLAlchemy model stores available codes. The existing
`Order.total` is preserved as the original subtotal; discounted amounts
are derived in the response schema. Tests cover all three discount tiers
and every defined error path.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (declarative `Mapped`
style), Pydantic v2

**Storage**: SQLite via SQLAlchemy — schema re-created from
`Base.metadata`; no migrations needed

**Testing**: pytest, `TestClient` (httpx) via the existing `client`
fixture in `tests/conftest.py`

**Target Platform**: Local/Linux server

**Project Type**: web-service

**Performance Goals**: < 200 ms response for discount application (single
indexed DB lookup)

**Constraints**: No new third-party dependencies

**Scale/Scope**: Small service; single discount code per order; no
concurrency concerns for this feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Stack — Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest | ✅ Pass | All used; no deviations |
| II. API Design — small route functions, Pydantic I/O, Depends | ✅ Pass | Single endpoint function; `DiscountApplyRequest` + `OrderWithDiscountOut` Pydantic models; `get_db` + `get_current_user` via Depends |
| III. Testing (NON-NEGOTIABLE) — ≥80% coverage, happy-path + error-path | ✅ Pass | Happy-path for 5%, 10%, 20% tiers + error paths for invalid, inactive, duplicate, 403, 404 |
| IV. Commit Convention — conventional commits | ✅ Pass | Target commit: `feat: add discount code apply endpoint` |
| V. Dependencies — no new third-party without justification | ✅ Pass | No new dependencies |
| VI. Type Safety — type hints on all public functions and handlers | ✅ Pass | All new functions and route handler will carry full type hints |
| VII. Scope Discipline — no unrelated refactoring | ✅ Pass | Only `models.py`, `routes/orders.py`, and `tests/test_orders.py` are touched |

**Post-design re-check**: All gates still pass after Phase 1 design.
No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/001-discount-codes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── apply-discount.md  # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code (repository root)

```text
src/api/
├── models.py            # Add DiscountCode model; add discount_code_id FK to Order
└── routes/
    └── orders.py        # Add POST /orders/{order_id}/apply-discount

tests/
└── test_orders.py       # Add discount code tests (happy-path + error-path)
```

**Structure Decision**: Single-project layout, extending the existing
`src/api/` tree. No new files or directories outside `models.py` and
`routes/orders.py`. All tests go into the existing `tests/test_orders.py`
to stay consistent with how order-related behaviour is tested today.

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
