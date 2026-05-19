# Implementation Plan: Order Refund

**Branch**: `001-order-refund` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-order-refund/spec.md`

## Summary

Add `POST /orders/{order_id}/refund` to the existing FastAPI service. The endpoint
authenticates the caller via the existing `X-User-Id` header dependency, verifies
order ownership, enforces a 30-day refund window, marks the order as refunded by
setting two new columns (`refunded`, `refunded_at`) on the `orders` table, and
returns a `RefundOut` response. All logic lives inline in `src/api/routes/orders.py`.
Tests cover the happy path and every rejection scenario.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI 0.115.0, SQLAlchemy 2.0.35, Pydantic v2.9.2,
pytest 8.3.3 — all already in `pyproject.toml`. No new dependencies.

**Storage**: SQLite via SQLAlchemy. Two new columns on `orders` table. No
migration needed; schema is recreated from `Base.metadata` at startup.

**Testing**: pytest with in-memory SQLite via the `client` fixture in
`tests/conftest.py`.

**Target Platform**: Linux/macOS server (development: local uvicorn)

**Project Type**: Web service (REST API)

**Performance Goals**: No specific targets — consistent with the rest of the
service (request/response in under 100ms on local SQLite).

**Constraints**: No new third-party dependencies. No new routes file. No
separate Refund database entity.

**Scale/Scope**: Single endpoint, two new DB columns, one new Pydantic model,
~5-8 new tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle                                                       | Status | Notes |
|-----------------------------------------------------------------|--------|-------|
| Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest | ✅ Pass | No stack changes |
| Idiomatic FastAPI: small routes, Pydantic models, Depends       | ✅ Pass | Route is inline; reuses `get_current_user` via `Depends` |
| Tests non-optional; 80% coverage; happy-path + error-path       | ✅ Pass | FR-008 mandates full test coverage; all scenarios covered |
| Conventional commits                                            | ✅ Pass | Commit messages will use `feat:` / `test:` prefixes |
| No new third-party dependencies without justification           | ✅ Pass | Only `datetime.timedelta` from stdlib used |
| Type hints on every public function and route handler           | ✅ Pass | All new functions/handlers will carry full type hints |
| Don't refactor unrelated code                                   | ✅ Pass | Only `models.py` (new columns) and `orders.py` (new route) touched |

**Post-design re-check**: All gates still pass. The 404-for-wrong-owner behaviour
diverges from the existing `GET /orders/{order_id}` (which returns 403), but this
is intentional per FR-003 and does not change the existing route.

## Project Structure

### Documentation (this feature)

```text
specs/001-order-refund/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── POST_orders_order_id_refund.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/api/
├── models.py            # ADD: refunded (bool), refunded_at (datetime | None) to Order
└── routes/
    └── orders.py        # ADD: RefundOut model + POST /orders/{order_id}/refund handler

tests/
└── test_orders.py       # ADD: refund endpoint tests (~7 new test functions)
```

**Structure Decision**: Single-project layout. The feature touches only the
existing `src/api/` tree. No new files outside of `orders.py` and `models.py`.

## Complexity Tracking

> No constitution violations. Table omitted.
