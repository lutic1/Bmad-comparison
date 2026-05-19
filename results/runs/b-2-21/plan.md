# Implementation Plan: Order Refund

**Branch**: `001-order-refund` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-order-refund/spec.md`

## Summary

Add `POST /orders/{order_id}/refund` to the existing FastAPI service. The
endpoint authenticates the caller via the existing `X-User-Id` header
(`get_current_user`), looks up the order, rejects when it does not exist
or does not belong to the caller, rejects when the order is older than
30 days, rejects when the order is already refunded, and otherwise marks
the order as refunded and creates a `Refund` row, returning the refund
record. A nullable `refunded_at` column is added to `Order` to track the
refunded state. A new `Refund` table records (`id`, `order_id` UNIQUE,
`amount`, `created_at`). Tests cover the happy path plus all rejection
paths.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (declarative
`Mapped[...]`), Pydantic v2

**Storage**: SQLite via SQLAlchemy. Schema created from `Base.metadata`
at startup; no migrations (per project convention).

**Testing**: pytest, FastAPI `TestClient`, in-memory SQLite (via the
existing `client` fixture in `tests/conftest.py`).

**Target Platform**: Local Python service (single process); same as the
rest of the service.

**Project Type**: web-service (single project, `src/` + `tests/`).

**Performance Goals**: No new performance targets; the endpoint
performs O(1) primary-key lookups and one or two inserts/updates.

**Constraints**: No new third-party dependencies. Stdlib first. Do not
refactor unrelated code. Authentication remains the existing
`X-User-Id` header convention.

**Scale/Scope**: Single endpoint, one new table, one new column on
`Order`, one new route module section, one new test module.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.0.0 principles vs. this plan:

| Principle | Status | Notes |
|-----------|--------|-------|
| Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest | ✅ | Uses the existing stack; no additions. |
| Idiomatic FastAPI (small routes, Pydantic models, Depends) | ✅ | New route is a single small handler reusing `get_db` and `get_current_user`. |
| Tests non-optional; ≥80% line coverage on changed files; happy + error path | ✅ | Test plan covers happy path and 5 error paths (unauth, not found, not owned, outside window, already refunded). |
| Conventional commits | ✅ | Commits will use `feat:` / `test:` prefixes. |
| No new third-party deps without justification | ✅ | None added. |
| Type hints on public functions and route handlers | ✅ | All new handlers/helpers are typed. |
| Don't refactor unrelated code in the same change | ✅ | Changes scoped to: `models.py` (additive), new `routes/refunds.py` or new section in `routes/orders.py`, router registration in `main.py`, new test file. |

**Result**: PASS. No violations; Complexity Tracking section not needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-order-refund/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── refund.openapi.yaml   # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
src/
└── api/
    ├── main.py                 # register new router
    ├── models.py               # +Refund table; +Order.refunded_at column
    ├── deps.py                 # unchanged
    └── routes/
        ├── orders.py           # unchanged
        └── refunds.py          # NEW — POST /orders/{order_id}/refund

tests/
├── conftest.py                 # unchanged
└── test_refunds.py             # NEW — happy + 5 error paths
```

**Structure Decision**: Single-project FastAPI layout already in place.
The refund endpoint is mounted under the existing `/orders` prefix via a
new router module (`api/routes/refunds.py`) registered in `main.py`,
keeping `orders.py` untouched (respects "don't refactor unrelated
code"). The new `Refund` model and new `Order.refunded_at` column live
in `api/models.py` alongside the existing models.

## Complexity Tracking

> Not applicable — Constitution Check passes without justified
> violations.
