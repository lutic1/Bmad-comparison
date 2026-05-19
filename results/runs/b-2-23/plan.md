# Implementation Plan: Order Refund

**Branch**: `001-order-refund` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-order-refund/spec.md`

## Summary

Add `POST /orders/{order_id}/refund` to the existing FastAPI service. The
endpoint authenticates via the existing `X-User-Id` header, looks up the
order, enforces ownership and a 30-day refund window, persists a new
`Refund` row, and marks the order as refunded via a new
`Order.refunded_at` column. Shipped with happy-path and one error-path
test per failure mode listed in spec FR-008.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI 0.115, SQLAlchemy 2.0 (declarative
`Mapped[...]`), Pydantic v2 — already in `pyproject.toml`. No new
third-party dependencies introduced.

**Storage**: SQLite via SQLAlchemy. Schema created at startup from
`Base.metadata` (no migrations — operator wipes `app.db` between runs,
per `CLAUDE.md`).

**Testing**: pytest with the existing in-memory SQLite `client` fixture
in `tests/conftest.py`.

**Target Platform**: Linux server (FastAPI/uvicorn).

**Project Type**: web-service (single project, existing `src/api/`
layout).

**Performance Goals**: N/A — feature inherits the service's existing
expectations.

**Constraints**: Must not introduce new dependencies; must not refactor
unrelated code; per-request DB session via `get_db`; auth via
`get_current_user`.

**Scale/Scope**: One new route, one new model, one new column, one
Pydantic response model, one test module.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution at `.specify/memory/constitution.md` v1.0.0. Checks:

- **Stack (Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest)**:
  ✅ All dependencies already present; no version changes.
- **Idiomatic FastAPI (small route, Pydantic in/out, `Depends`)**: ✅
  Plan uses a single small handler in `src/api/routes/orders.py`,
  Pydantic response model, `Depends(get_db)` + `Depends(get_current_user)`.
- **Tests non-optional; ≥80% coverage on changed files; happy + ≥1
  error path per new route**: ✅ Test plan covers happy path plus one
  test per FR-008 failure mode (unauthenticated, not-owner/not-found,
  window expired, already refunded). Changed files are the new route
  block, the new model, and the new test module — all directly exercised.
- **Conventional commits**: ✅ Commits will use `feat:` / `test:` /
  `refactor:` prefixes.
- **No new third-party dependencies without justification**: ✅ None added.
- **Type hints on public functions / route handlers**: ✅ All new public
  callables typed.
- **No unrelated refactors**: ✅ Plan touches only refund-related code.

Result: PASS — no violations, Complexity Tracking section left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-order-refund/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── refund.openapi.yaml
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/api/
├── deps.py              # unchanged — reuses get_db, get_current_user
├── main.py              # unchanged
├── models.py            # +Order.refunded_at column, +Refund model
└── routes/
    └── orders.py        # +POST /orders/{order_id}/refund handler
                         # +RefundOut Pydantic model

tests/
└── test_refunds.py      # NEW — happy path + one test per FR-008 failure mode
```

**Structure Decision**: Single-project FastAPI service; reuse existing
`src/api/` layout. No new packages or directories — the refund route
belongs alongside the existing `orders` routes in `src/api/routes/orders.py`,
the `Refund` model lives in `src/api/models.py`, and refund tests get
their own module under `tests/`.

## Complexity Tracking

> Constitution Check passed with no violations. No complexity tracking
> entries required.
