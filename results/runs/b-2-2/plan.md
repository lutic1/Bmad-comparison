# Implementation Plan: Order Refund

**Branch**: `001-order-refund` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-order-refund/spec.md`

## Summary

Add `POST /orders/{order_id}/refund` to the existing orders router. The endpoint authenticates via the existing `X-User-Id` mechanism, verifies the order exists and belongs to the caller, enforces a strict 30-day refund window, persists two new columns on the `Order` model (`refunded`, `refunded_at`), and returns a `RefundOut` Pydantic response. Tests cover the happy path and all five rejection scenarios.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (declarative `Mapped[...]` style), Pydantic v2

**Storage**: SQLite via SQLAlchemy — two new columns added to `orders` table. Schema is recreated from `Base.metadata.create_all` at startup; no migration script needed (operator wipes `app.db` between runs).

**Testing**: pytest — new tests added to `tests/test_orders.py` using the existing `client` fixture and in-memory SQLite.

**Target Platform**: Linux/macOS server

**Project Type**: Web service (REST API)

**Performance Goals**: Consistent with existing endpoints — no new performance requirements.

**Constraints**: No new third-party dependencies; stdlib `datetime` and `timedelta` only.

**Scale/Scope**: Single endpoint addition to an existing single-process SQLite service.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Technology Stack | ✅ PASS | Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest — all existing |
| II. API Design | ✅ PASS | Small route function, Pydantic response model, `Depends(get_db)` + `Depends(get_current_user)` |
| III. Testing (NON-NEGOTIABLE) | ✅ PASS | Happy path + 5 individual error-path tests; 80%+ line coverage on all changed files |
| IV. Commit Standards | ✅ PASS | `feat: add POST /orders/{id}/refund endpoint` |
| V. Dependency Management | ✅ PASS | No new dependencies; stdlib `datetime`/`timedelta` only |
| VI. Type Safety | ✅ PASS | Type hints on route handler and `RefundOut` Pydantic model |
| VII. Change Discipline | ✅ PASS | Only `models.py`, `routes/orders.py`, `tests/test_orders.py` are touched |

No violations — no Complexity Tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/001-order-refund/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── api/
    ├── models.py              # Add refunded: bool + refunded_at: Optional[datetime] to Order
    └── routes/
        └── orders.py          # Add RefundOut model + POST /{order_id}/refund route

tests/
└── test_orders.py             # Add refund happy-path + 5 rejection-scenario tests
```

**Structure Decision**: Single-project layout, extending three existing files. No new modules or packages warranted for a single endpoint addition.
