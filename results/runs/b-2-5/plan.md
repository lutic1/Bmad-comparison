# Implementation Plan: Order Refund Endpoint

**Branch**: `001-order-refund` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-order-refund/spec.md`

## Summary

Add `POST /orders/{order_id}/refund`. The endpoint authenticates the caller via
the existing `X-User-Id` header, looks up the order, verifies ownership, checks
the 30-day eligibility window against `Order.created_at`, ensures the order has
not already been refunded, marks the order as refunded, persists a `Refund`
row, and returns the refund record. Implementation follows the patterns
already in `src/api/routes/orders.py`: a small route function on the existing
orders router, Pydantic v2 response model, dependency injection via `Depends`,
and SQLAlchemy 2.x for persistence. Schema is created from `Base.metadata` at
startup; no migration is written (per `CLAUDE.md`).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI 0.115.x, SQLAlchemy 2.0.x, Pydantic v2,
Starlette (transitive). No new third-party dependencies.

**Storage**: SQLite via SQLAlchemy (existing engine in `api/deps.py`). Schema
created from `Base.metadata` at startup; operator wipes `app.db` between runs.

**Testing**: pytest 8.x using the existing `client` fixture in
`tests/conftest.py` (in-memory SQLite per test).

**Target Platform**: Linux/macOS server process (uvicorn).

**Project Type**: Web service (single project, single backend).

**Performance Goals**: N/A beyond the existing service baseline. A refund is a
single-row insert plus a single-row update.

**Constraints**: Refund eligibility is bounded to 30 days from
`Order.created_at` (inclusive of the 30th day per spec Assumptions). Refunds
are all-or-nothing and a given order can be refunded at most once.

**Scale/Scope**: Small synthetic service; no scale targets beyond
correctness.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` v1.0.0.

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Stack (Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest) | ✅ | Uses the existing stack; no new tools. |
| II | Idiomatic FastAPI (small routes, Pydantic models, Depends) | ✅ | One small route on the existing `/orders` router, two Pydantic response models, `Depends(get_db)` and `Depends(get_current_user)`. |
| III | Tests non-optional; ≥80% line coverage on changed files; happy-path + ≥1 error-path test per new route | ✅ | Plan ships with happy-path + 4 error-path tests (unauth, not-found, not-owner, expired-window, double-refund). |
| IV | Conventional commits | ✅ | Commit messages will use `feat:` / `test:` / `docs:` prefixes. |
| V | No new third-party dependencies without justification | ✅ | No new dependencies. |
| VI | Type hints on every public function and route handler | ✅ | Route handler and any helpers carry full type hints; Pydantic models are typed. |
| VII | Don't refactor unrelated code | ✅ | Touch only what is needed: add `Order.refunded_at`, add `Refund` model, add one route, add tests. Existing route handlers, helpers, and tests left untouched. |

**Result**: PASS. No violations. Complexity Tracking table intentionally
omitted.

## Project Structure

### Documentation (this feature)

```text
specs/001-order-refund/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── refund-endpoint.md   # POST /orders/{order_id}/refund contract
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
src/
└── api/
    ├── deps.py              # existing — reuse get_db, get_current_user
    ├── models.py            # CHANGE: add refunded_at to Order; add Refund
    ├── main.py              # no change (router already mounted)
    └── routes/
        ├── orders.py        # CHANGE: add POST /orders/{order_id}/refund route + Pydantic models
        └── users.py         # no change

tests/
├── conftest.py              # no change — existing client fixture is sufficient
├── test_orders.py           # no change
└── test_refunds.py          # NEW — happy path + error paths for the refund endpoint
```

**Structure Decision**: Single-project layout (already in use). The new route
lives on the existing `orders` router rather than a new module, matching the
"small route function" guidance in the constitution and the existing pattern
in `src/api/routes/orders.py`. A dedicated `tests/test_refunds.py` keeps
refund-specific tests discoverable without modifying the existing
`tests/test_orders.py`.

## Complexity Tracking

> No constitutional violations to justify.
