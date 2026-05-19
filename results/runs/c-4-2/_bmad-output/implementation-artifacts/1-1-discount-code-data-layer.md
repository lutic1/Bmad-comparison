# Story 1.1: Discount Code Data Layer

Status: done

## Story

As a developer,
I want the `DiscountCode` model and extended `Order` columns in place,
so that the checkout API in Story 1.2 has a schema foundation to build on.

## Context

The `target` service stores all monetary values as **integer cents** (`Integer` columns, never floats). The schema is created entirely by `Base.metadata.create_all(bind=engine)` at startup — there are no migrations; the operator wipes `app.db` between runs. Tests use an in-memory `sqlite://` database via `StaticPool`, which also picks up schema from `Base.metadata`. This story is purely additive: no existing behaviour changes, no routes touched.

## Acceptance Criteria

1. `src/api/models.py` contains a new `DiscountCode` class (table `discount_codes`) with columns: `id` (PK), `code` (String 64, unique, not null), `percentage` (Integer, not null), `is_active` (Boolean, default True, not null), `max_uses` (Integer, nullable), `times_used` (Integer, default 0, not null).
2. `Boolean` is added to the `sqlalchemy` import in `models.py` (currently only `DateTime, ForeignKey, Integer, String` are imported — `Boolean` is missing and will cause a startup crash if not added).
3. `Order` has three new columns: `original_total` (Integer, not null, default 0), `discount_code` (String 64, nullable), `discount_percentage` (Integer, nullable).
4. `tests/conftest.py` has a new `db` fixture derived from the existing `db_engine` fixture, yielding a `Session` scoped to the test function.
5. `pytest` passes with zero failures (all existing tests continue to pass).

## Tasks / Subtasks

- [x] Update `src/api/models.py` (AC: 1, 2, 3)
  - [x] Add `Boolean` to the `sqlalchemy` import line
  - [x] Add `DiscountCode` class after `OrderItem`
  - [x] Add `original_total`, `discount_code`, `discount_percentage` columns to `Order`
- [x] Update `tests/conftest.py` (AC: 4)
  - [x] Add `db` fixture derived from `db_engine`
- [x] Verify (AC: 5)
  - [x] Run `pytest` — must pass with zero failures

## Dev Notes

### Critical Conventions (from convention sweep)

- **Money = integer cents.** `original_total` and `discount_percentage` are `Integer`. Never use `Float` for any monetary or percentage column.
- **`Boolean` is NOT currently imported** in `models.py`. The import line is `from sqlalchemy import DateTime, ForeignKey, Integer, String`. Add `Boolean` to this line — omitting it causes an `AttributeError` at startup before any tests run.
- **Schema is auto-created.** `Base.metadata.create_all` runs in `main.py` lifespan and in `conftest.py` `db_engine` fixture. No migration file needed.
- **`Mapped[...]` + `mapped_column(...)` pattern** is used for all columns (SQLAlchemy 2.x declarative style). Follow the exact same style as `User`, `Order`, `OrderItem` — no legacy `Column(...)` syntax.
- **`db` fixture shares the same in-memory DB as `client`.** Both derive from `db_engine` (same `StaticPool` instance). Tests declaring `(client, db)` parameters see the same database state.

### Exact model pattern to follow

```python
# Existing pattern (copy exactly):
id: Mapped[int] = mapped_column(Integer, primary_key=True)
code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
percentage: Mapped[int] = mapped_column(Integer, nullable=False)
is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
```

### New columns on `Order` — insert after `created_at`

```python
original_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
discount_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
discount_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

### `db` fixture for `tests/conftest.py`

```python
@pytest.fixture
def db(db_engine):
    from sqlalchemy.orm import sessionmaker as _sm
    Session = _sm(bind=db_engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
```

### What NOT to do

- Do not touch any route files — that is Story 1.2.
- Do not add a relationship from `Order` back to `DiscountCode` — the order stores `discount_code` as a plain string column, not a FK. The PRD explicitly does not require referential integrity here.
- Do not add `DiscountCode` to the `User` or `Order` relationship graph.

### Project Structure Notes

- Only two files change: `src/api/models.py` and `tests/conftest.py`.
- No new files.
- No `pyproject.toml` changes — `Boolean` is part of `sqlalchemy` which is already a dependency.

### References

- Architecture: `_bmad-output/planning-artifacts/architecture/discount-codes-architecture.md` §4
- PRD FR-1: `_bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md` §4.1
- Existing model style: `src/api/models.py`
- Existing conftest: `tests/conftest.py`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `Boolean` to sqlalchemy import in models.py
- Added `DiscountCode` model with 6 columns (id, code, percentage, is_active, max_uses, times_used)
- Added 3 new nullable/defaulted columns to `Order` (original_total, discount_code, discount_percentage)
- Added `db` session fixture to conftest.py derived from `db_engine`
- 11/11 existing tests pass; no regressions

### File List

- src/api/models.py
- tests/conftest.py
