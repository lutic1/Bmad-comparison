# Story 1.1: Discount Code Data Layer

Status: review

## Story

As a developer laying the foundation for the discount-code feature,
I want to add the `DiscountCode` ORM model, extend `Order` with two nullable audit columns, seed the three canonical codes at startup, and expose test fixtures that seed the same codes into the in-memory test database,
so that Story 1.2 can wire discount logic against a real schema with no further model work.

## Acceptance Criteria

1. A `DiscountCode` SQLAlchemy model exists in `src/api/models.py` with columns `id` (PK), `code` (String(64), unique, not-null), `percentage` (Integer, not-null). It inherits from `Base` so `Base.metadata.create_all` creates the table automatically.
2. The `Order` model in `src/api/models.py` has two new nullable columns: `discount_code` (String(64), nullable, default None) and `discount_pct` (Integer, nullable, default None).
3. `src/api/main.py` calls a private `_seed_discount_codes()` function immediately after `Base.metadata.create_all` inside the `lifespan` context manager. The function inserts `("SAVE5", 5)`, `("SAVE10", 10)`, `("SAVE20", 20)` if they do not already exist. It is idempotent (safe to call on every restart).
4. `tests/conftest.py` gains two new fixtures: `db(db_engine)` — yields a `Session` bound to the test engine — and `discount_codes(db)` — inserts the same three canonical codes and commits. Both fixtures follow the existing teardown pattern (close in `finally`).
5. `pytest` passes with zero failures after this story (all pre-existing tests still green; no new tests required for this story).

## Tasks / Subtasks

- [x] Add `DiscountCode` model to `src/api/models.py` (AC: 1)
  - [x] Place after `OrderItem` class; inherit from `Base`
  - [x] Columns: `id` Integer PK, `code` String(64) unique not-null, `percentage` Integer not-null
  - [x] Store codes in UPPER CASE by convention (enforced at seed time; no DB constraint needed)
- [x] Extend `Order` model with two nullable columns (AC: 2)
  - [x] `discount_code: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)`
  - [x] `discount_pct: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)`
  - [x] Place after `created_at` field
- [x] Add `_seed_discount_codes()` and wire into `lifespan` in `src/api/main.py` (AC: 3)
  - [x] Import `DiscountCode` from `api.models` and `SessionLocal` from `api.deps`
  - [x] Helper queries each code with `.one_or_none()`; inserts only if absent; single `db.commit()`
  - [x] Call `_seed_discount_codes()` on the line immediately after `Base.metadata.create_all(bind=engine)`
- [x] Add `db` and `discount_codes` fixtures to `tests/conftest.py` (AC: 4)
  - [x] `db` fixture: `sessionmaker(bind=db_engine, ...)()`, yield, close in finally
  - [x] `discount_codes` fixture: add three `DiscountCode` rows, `db.commit()`
  - [x] Import `DiscountCode` from `api.models` at top of conftest
- [x] Run `pytest` and confirm all existing tests pass (AC: 5)

## Dev Notes

**Critical conventions from the codebase — read before touching any file:**

- **No migrations.** Schema is rebuilt from `Base.metadata.create_all` at startup. Adding `DiscountCode` and the two `Order` columns requires only Python changes; the operator wipes `app.db` between runs.
- **`SessionLocal` is in `api.deps`**, not `api.main`. Import it from there for `_seed_discount_codes()`.
- **`autoflush=False, autocommit=False`** on `SessionLocal` — be explicit: flush/commit manually.
- **`db_engine` fixture uses `StaticPool`** (in-memory SQLite). The `db` fixture must bind to that same engine, not create a new one.
- **Do NOT use `with SessionLocal() as db:`** in `_seed_discount_codes()` unless `SessionLocal` supports context manager protocol — the existing codebase uses explicit `.close()` in `finally`. Check `deps.py` before choosing the pattern.
- **`DiscountCode` must appear in `src/api/models.py` before it is imported anywhere else** — add it after `OrderItem` to keep related models together.
- **`discount_codes` fixture depends on `db`, which depends on `db_engine`**, which depends on nothing. The `client` fixture also depends on `db_engine`. pytest handles this correctly; no circular dependency.
- **Dead code at bottom of `orders.py`** (`adjust_total`, `add_item_inline`, `_format_created_at`) — do not touch or replicate these functions.

### Project Structure Notes

- `src/api/models.py` — extend in-place; no new files
- `src/api/main.py` — extend `lifespan`; add `_seed_discount_codes()` as module-level private function
- `tests/conftest.py` — append two fixtures at the bottom

### References

- Architecture §2 Data Model Changes [Source: `_bmad-output/planning-artifacts/architecture.md#2-data-model-changes`]
- Architecture §4 Seeding [Source: `_bmad-output/planning-artifacts/architecture.md#4-seeding`]
- Architecture §6 File Change Summary [Source: `_bmad-output/planning-artifacts/architecture.md#6-file-change-summary`]
- PRD FR-1 Discount code storage [Source: `_bmad-output/planning-artifacts/prds/prd-target-2026-05-18/prd.md#fr-1`]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- pytest runner located at `.venv/bin/pytest` (not on PATH)

### Completion Notes List

- Added `DiscountCode` model to `src/api/models.py` after `OrderItem`; inherits `Base`; `code` unique String(64), `percentage` Integer
- Added `discount_code` (String(64), nullable) and `discount_pct` (Integer, nullable) columns to `Order` model after `created_at`
- Added `_seed_discount_codes()` to `src/api/main.py`; uses explicit try/finally pattern matching `get_db()`; called in `lifespan` after `create_all`
- Added `db` and `discount_codes` fixtures to `tests/conftest.py`; `db` binds to test engine via `sessionmaker`; `discount_codes` inserts SAVE5/SAVE10/SAVE20
- All 11 existing tests pass; 0 regressions

### File List

- `src/api/models.py`
- `src/api/main.py`
- `tests/conftest.py`
