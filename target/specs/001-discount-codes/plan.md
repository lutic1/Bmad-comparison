# Implementation Plan: Percentage Discount Codes at Checkout

**Branch**: `001-discount-codes` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-discount-codes/spec.md`

## Summary

Add an endpoint that lets the order's owner apply one of three
percentage discount codes (5%, 10%, 20%) to an existing order, replacing
any code already applied. The order persists the original subtotal, the
applied code, and the resulting (discounted) total — all in integer
cents, consistent with the existing orders schema. Codes are
case-insensitive and limited to a fixed in-code mapping; no new
third-party dependencies, no migrations (operator wipes `app.db`).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (declarative
`Mapped[...]`), Pydantic v2 — all already in `pyproject.toml`. No new
third-party dependencies.

**Storage**: SQLite via SQLAlchemy (`sqlite:///./app.db`). Schema is
created from `Base.metadata` at startup; no migrations.

**Testing**: pytest with the existing `client` fixture in
`tests/conftest.py` (in-memory SQLite per test, dependency overrides).

**Target Platform**: Linux server (FastAPI ASGI app); local dev via
uvicorn.

**Project Type**: Single web service (FastAPI). Layout already exists
under `src/api/`.

**Performance Goals**: N/A beyond existing service expectations.
Discount application is O(1).

**Constraints**: Money handled exclusively in integer cents to avoid
binary-float drift (matches existing `Order.total` column). Half-up
rounding on the cents result.

**Scale/Scope**: Three valid codes, one new endpoint, two new columns
on `orders`. No usage tracking, no per-user limits, no expiry (out of
scope per spec Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Validated against `.specify/memory/constitution.md` v1.0.0:

- **Stack (Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest)** — PASS. No additions; uses what's installed.
- **Idiomatic FastAPI (small route fns, Pydantic models, `Depends`)** — PASS. New endpoint is a single small handler using `Depends(get_db)` and `Depends(get_current_user)`.
- **Tests non-optional; ≥80% line coverage on changed files; happy + error path per new route** — PASS. Plan ships happy paths for all three percentages, an invalid-code 400, a 404 for unknown orders, a 403 for non-owners, and the replace-existing-code case. New code is concentrated in one route + a tiny helper, easily covered by these tests.
- **Conventional commits** — PASS (commit messages controlled at commit time, e.g., `feat: add discount code endpoint`).
- **No new third-party deps without justification** — PASS. None added.
- **Type hints on every public function / route handler** — PASS. All new public signatures will be annotated.
- **Don't refactor unrelated code in the same change** — PASS. Existing order creation, models, and routes remain untouched except for the two additive columns on `Order` and the new route handler. Pre-existing oddities (e.g. the `%Y-%d-%m` date format in `routes/orders.py`) are intentionally left alone.

No violations → Complexity Tracking section omitted.

## Project Structure

### Documentation (this feature)

```text
specs/001-discount-codes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── discount-endpoint.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/
└── api/
    ├── main.py              # unchanged
    ├── deps.py              # unchanged (reuse get_db, get_current_user)
    ├── models.py            # +Order.subtotal, +Order.discount_code
    └── routes/
        ├── orders.py        # +POST /orders/{order_id}/discount, +OrderOut fields
        └── users.py         # unchanged

tests/
├── conftest.py              # unchanged
├── test_orders.py           # unchanged
├── test_users.py            # unchanged
├── test_dates.py            # unchanged
└── test_discounts.py        # NEW — covers FR-001..FR-009, SC-001..SC-004
```

**Structure Decision**: Stay with the existing single-project FastAPI
layout under `src/api/`. New behaviour lives entirely in
`src/api/routes/orders.py` plus two additive columns in
`src/api/models.py`. Tests for the feature live in
`tests/test_discounts.py` so order tests stay focused.

