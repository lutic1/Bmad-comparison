# Implementation Plan: Order Refund

**Branch**: `001-order-refund` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-order-refund/spec.md`

## Summary

Add `POST /orders/{order_id}/refund` to the existing FastAPI service. The
endpoint authenticates via the existing `X-User-Id` header
(`get_current_user` dependency), verifies the order exists and belongs to
the requester, rejects orders older than 30 days, creates a `Refund`
row tied to the order, marks the order as refunded by setting a new
nullable `refunded_at` column, and returns the refund record. Idempotency
of "one refund per order" is enforced at the DB level via a unique
constraint on `refunds.order_id`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (declarative `Mapped[...]`), Pydantic v2

**Storage**: SQLite via SQLAlchemy (schema created from `Base.metadata` at startup; no migrations)

**Testing**: pytest with the existing `client` fixture in `tests/conftest.py` (in-memory SQLite per test)

**Target Platform**: Linux server (small FastAPI service)

**Project Type**: web-service (single project — existing layout under `src/api/`)

**Performance Goals**: N/A — small service; inherits FastAPI defaults

**Constraints**:
- No new third-party dependencies (constitution).
- No new logging/metrics/middleware (project CLAUDE.md).
- Reuse existing auth dependency rather than re-implementing.
- 30-day window measured from `Order.created_at` to request-receipt time using the service's clock.

**Scale/Scope**: Single endpoint, one new table (`refunds`), one new column (`orders.refunded_at`), ~5–6 tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest | ✅ | Plan uses exactly this stack; no additions. |
| Idiomatic FastAPI (small routes, Pydantic models, Depends) | ✅ | One route function; Pydantic `RefundOut`; depends on `get_current_user` and `get_db`. |
| Tests non-optional; ≥80% line coverage on changed files; happy + ≥1 error-path test per new route | ✅ | Phase 1 enumerates 1 happy-path test plus 5 error-path tests covering every FR rejection branch. |
| Conventional commits | ✅ | Implementation work will land under `feat: …` commits. |
| No new third-party dependencies without justification | ✅ | None added. |
| Type hints on every public function and route handler | ✅ | Plan mandates type hints on the new route and its Pydantic models. |
| Don't refactor unrelated code in the same change | ✅ | Plan touches only: `models.py` (add `refunded_at` + `Refund`), `routes/orders.py` (add one handler), one new test file. |

**Result: PASS** — no violations, Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-order-refund/
├── plan.md              # This file (/speckit-plan command output)
├── spec.md              # Feature spec
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── refund-endpoint.md
└── checklists/
    └── requirements.md  # From /speckit-specify
```

### Source Code (repository root)

```text
src/
└── api/
    ├── deps.py              # (unchanged — reuse get_current_user, get_db)
    ├── main.py              # (unchanged — router already mounted)
    ├── models.py            # MODIFIED: add Order.refunded_at; add Refund model
    └── routes/
        └── orders.py        # MODIFIED: add POST /orders/{order_id}/refund handler + RefundOut Pydantic model

tests/
└── test_refunds.py          # NEW: happy path + 5 error-path tests
```

**Structure Decision**: Use the existing single-project FastAPI layout under
`src/api/`. The refund endpoint lives in the existing `orders` router
(`src/api/routes/orders.py`) because the route is prefixed `/orders/...`
and the constitution forbids creating abstractions for a single call
site. The `Refund` model is added to `src/api/models.py` alongside the
existing models. Tests live in a new `tests/test_refunds.py` mirroring
the existing `test_orders.py` / `test_users.py` pattern.

## Complexity Tracking

> No Constitution Check violations — section intentionally empty.
