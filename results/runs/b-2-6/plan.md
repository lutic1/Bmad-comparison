# Implementation Plan: Order Refund

**Branch**: `001-order-refund` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-order-refund/spec.md`

## Summary

Add `POST /orders/{order_id}/refund` to the existing FastAPI service. The
endpoint authenticates the caller via the existing `X-User-Id` header
(`get_current_user`), looks up the order, enforces ownership and a 30-day
refund window, records a single `Refund` row, marks the order as refunded
(new `refunded_at` column on `orders`), and returns the refund record.
Tests cover the happy path and each rejection path.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (declarative `Mapped[...]`),
Pydantic v2

**Storage**: SQLite via SQLAlchemy, schema created from `Base.metadata` at
startup (no migrations — operator wipes `app.db` between runs)

**Testing**: pytest with the existing `client` fixture in
`tests/conftest.py` (in-memory SQLite per test)

**Target Platform**: Linux server (local FastAPI app)

**Project Type**: Single-project web service

**Performance Goals**: Match existing endpoints (single SQLite write, no
hot-path concerns)

**Constraints**: No new third-party dependencies; no logging / metrics /
middleware additions; no migrations; no auth rework — reuse
`api.deps.get_current_user`

**Scale/Scope**: Small demo service; one new endpoint, one new model, one
column added to `orders`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.0.0 (`.specify/memory/constitution.md`):

- **Stack — Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest**:
  PASS. No additions outside this stack.
- **Idiomatic FastAPI — small route functions, Pydantic request/response,
  `Depends`**: PASS. Route is a single small function; request body is
  empty; response is a `RefundOut` Pydantic model; uses
  `Depends(get_db)` and `Depends(get_current_user)`.
- **Tests are non-optional, ≥80% line coverage on changed files, happy +
  error path per new route**: PASS. Test plan covers happy path plus four
  error paths (no auth, not found, not owned, outside window,
  already-refunded), exceeding the minimum.
- **Conventional commits**: Out of scope for the plan itself; will apply
  at commit time (`feat: add POST /orders/{id}/refund`).
- **No new third-party dependencies without justification**: PASS. None
  added.
- **Type hints on public functions and route handlers**: PASS. Route and
  helpers carry full annotations.
- **Don't refactor unrelated code in the same change**: PASS. Touches
  only `models.py`, `routes/orders.py` (additive), and the new test file.

No violations → Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-order-refund/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── refund.openapi.yaml
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── api/
    ├── deps.py              # unchanged — get_db, get_current_user
    ├── main.py              # unchanged — routers already registered
    ├── models.py            # +Refund model, +Order.refunded_at column
    └── routes/
        └── orders.py        # +POST /orders/{order_id}/refund handler
                             # +RefundOut Pydantic model

tests/
└── test_refunds.py          # new — happy path + error paths
```

**Structure Decision**: Reuse the existing single-project FastAPI layout
under `src/api/`. The refund endpoint lives on the existing orders router
(`src/api/routes/orders.py`) because it is keyed by `order_id`; this
matches how `GET /orders/{order_id}` is already organised. The new
`Refund` model goes in `src/api/models.py` alongside `Order` and
`OrderItem`. Tests go in `tests/test_refunds.py` to keep one test file
per resource.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations.
