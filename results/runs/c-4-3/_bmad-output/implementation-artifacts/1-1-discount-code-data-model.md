# Story 1.1: Discount Code Data Model

Status: review

## Story

As a developer laying the foundation for the discount-code feature,
I want to add a `DiscountCode` SQLAlchemy model and two nullable columns to the `Order` model,
so that the database schema is ready for the checkout-integration story and the service starts cleanly with no regressions.

## Acceptance Criteria

1. A `DiscountCode` class exists in `src/api/models.py`, subclasses `Base`, maps to table `discount_codes`, and has columns: `id` (Integer PK), `code` (String(64), unique, non-nullable), `percentage` (Integer, non-nullable). The `unique=True` on `code` creates the required DB-level unique index.
2. `Order` in `src/api/models.py` gains two new nullable columns: `discount_code` (String(64), nullable, default None) and `discounted_total` (Integer, nullable, default None). Both use the existing `Mapped[T | None]` declarative style.
3. No existing tests break (`pytest` passes 100 % green).
4. The service starts (`GET /health` returns 200) with the new schema in a fresh SQLite database.
5. `DiscountCode` is importable from `api.models` (i.e. the class is defined in the same `models.py` file alongside `User`, `Order`, `OrderItem`).

## Tasks / Subtasks

- [x] Add `DiscountCode` model to `src/api/models.py` (AC: 1, 5)
  - [x] Place after `OrderItem` class, before end of file
  - [x] Use `Mapped[int]`, `Mapped[str]` declarative style — no bare `Column()`
  - [x] `code`: `Mapped[str] = mapped_column(String(64), unique=True, nullable=False)`
  - [x] `percentage`: `Mapped[int] = mapped_column(Integer, nullable=False)`
  - [x] No relationship back-reference to `Order` needed
- [x] Add `discount_code` and `discounted_total` columns to `Order` in `src/api/models.py` (AC: 2)
  - [x] `discount_code: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)`
  - [x] `discounted_total: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)`
  - [x] Both columns placed after `created_at` in the `Order` class body
- [x] Verify `pytest` passes with no changes to any test files (AC: 3)
- [x] Smoke-test startup (AC: 4) — `Base.metadata.create_all` will auto-pick up both changes

## Dev Notes

**Critical conventions to follow (from convention sweep):**

- All new columns use `Mapped[type] = mapped_column(...)` style — never bare `Column(...)`. SQLAlchemy 2.x declarative only.
- Nullable optional columns use `Mapped[str | None]` and `Mapped[int | None]` — not `Optional[str]`.
- `created_at` on existing models uses `default=datetime.utcnow` (callable reference, not a call). If you add timestamps to `DiscountCode` in the future, match that pattern. This story does NOT add `created_at` to `DiscountCode`.
- No migrations exist. Schema is built from `Base.metadata.create_all` at startup. The test fixture `db_engine` calls this automatically — `DiscountCode` will appear in every test's in-memory SQLite as long as it subclasses `Base` and is defined in `models.py` (which is imported before the fixture runs via `from api.models import Base`).
- Do NOT add a relationship from `DiscountCode` back to `Order`. No join is needed at query time in v1.

**What this story does NOT touch:**
- `src/api/routes/orders.py` — no schema or logic changes
- `src/api/deps.py`, `src/api/main.py`, `src/api/utils/` — untouched
- All existing test files — untouched; they must pass as-is

### Project Structure Notes

- Single file changes: `src/api/models.py` only.
- `DiscountCode` class goes at the end of the file, after `OrderItem`.
- New columns on `Order` go after the existing `created_at` line.

### References

- Architecture doc: `_bmad-output/planning-artifacts/architecture.md` — §3 Data Model
- PRD: `_bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md` — FR-4

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Added `DiscountCode` class after `OrderItem` in `src/api/models.py`. Uses `Mapped[str]`/`Mapped[int]` declarative style with `unique=True` on `code`.
- Added `discount_code: Mapped[str | None]` and `discounted_total: Mapped[int | None]` to `Order`, placed after `created_at`.
- All 11 pre-existing tests pass; no test files modified.

### File List

- src/api/models.py
