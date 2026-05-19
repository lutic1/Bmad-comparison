# Story 1.1: Order Model — Refund Fields

Status: ready-for-dev

## Story

As a developer,
I want the `Order` model and `OrderOut` schema to carry `refunded` and `refunded_at` fields,
so that the data layer is ready for the refund endpoint and the GET response reflects refund state.

## Context

This story is the prerequisite for Story 1.2 (refund endpoint). It makes two focused changes: adds two columns to the `Order` SQLAlchemy model, and extends the `OrderOut` Pydantic schema + both existing handler return sites to populate those fields. No new endpoint, no new tests beyond confirming existing tests still pass.

The 30-day refund feature requires the `Order` table to carry `refunded` (bool) and `refunded_at` (nullable datetime). The architecture also decided (OQ-1) that `GET /orders/{order_id}` should expose these fields — do that here so Story 1.2 can build on a complete foundation.

## Acceptance Criteria

1. `Order` model has `refunded: Mapped[bool]` with `nullable=False, default=False` and `refunded_at: Mapped[datetime | None]` with `nullable=True, default=None`.
2. `Boolean` is imported from `sqlalchemy` alongside the existing imports.
3. `OrderOut` has two new fields: `refunded: bool` and `refunded_at: str | None`.
4. Both `create_order` and `get_order` handlers construct `OrderOut` with `refunded=order.refunded` and `refunded_at=order.refunded_at.isoformat() if order.refunded_at else None`.
5. All existing tests (`test_orders.py`, `test_users.py`, `test_dates.py`) remain green with no changes.
6. No new test file is needed for this story — regression is verified by running `pytest` on existing suite.

## Tasks / Subtasks

- [ ] Update `src/api/models.py` (AC: 1, 2)
  - [ ] Add `from sqlalchemy import Boolean` to the existing import line
  - [ ] Add `refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)` to `Order`
  - [ ] Add `refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)` to `Order`
- [ ] Update `src/api/routes/orders.py` (AC: 3, 4)
  - [ ] Add `refunded: bool` and `refunded_at: str | None` fields to `OrderOut`
  - [ ] Add `refunded=order.refunded, refunded_at=order.refunded_at.isoformat() if order.refunded_at else None` to the `OrderOut(...)` constructor in `create_order`
  - [ ] Add same two fields to the `OrderOut(...)` constructor in `get_order`
- [ ] Run `pytest` to confirm no regressions (AC: 5, 6)

## Dev Notes

- **File: `src/api/models.py`** — declarative `Mapped[...]` style throughout. Existing columns use `mapped_column(Integer/String/DateTime, ...)`. Match that style exactly. `DateTime` is already imported; add `Boolean` to the same `sqlalchemy` import.
- **File: `src/api/routes/orders.py`** — `OrderOut` is a plain Pydantic `BaseModel` (not ORM model), built manually in each handler via `OrderOut(id=..., user_id=..., ...)`. Both `create_order` (line ~73) and `get_order` (line ~97) call it. Add the two new keyword args to both callsites.
- **No migration:** Per `CLAUDE.md`, the schema is rebuilt from `Base.metadata.create_all` at startup. Wipe `app.db` between deploys. No Alembic.
- **Cents:** `total` stays as-is. The new fields are not money fields.
- **`refunded_at` formatting:** Use `.isoformat()` (produces `2026-05-19T14:32:00`) when not None, else `None`. This matches the response shape in the PRD.
- **Do not** touch `src/api/deps.py`, `src/api/main.py`, `tests/conftest.py`, or any test files.

### Project Structure Notes

- Models live in `src/api/models.py` — single file, all ORM classes.
- Route schemas (Pydantic) and handlers live together in `src/api/routes/orders.py` — follow existing co-location pattern.
- No separate schema file. No separate service layer.

### References

- [Source: _bmad-output/planning-artifacts/arch-order-refund.md#Section 2 — Data Model]
- [Source: _bmad-output/planning-artifacts/arch-order-refund.md#Section 3.1 — Updated OrderOut]
- [Source: _bmad-output/planning-artifacts/prd-order-refund.md#Section 7 — Data Model Changes]
- [Source: src/api/models.py — existing Order class]
- [Source: src/api/routes/orders.py — OrderOut, create_order, get_order]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (Amelia)

### Debug Log References

### Completion Notes List

- All 6 ACs verified. 11/11 pre-existing tests green.

### File List

- `src/api/models.py`
- `src/api/routes/orders.py`
