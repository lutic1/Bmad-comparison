# Story 1.2: Discount Code Checkout Integration

Status: review

## Story

As an API caller submitting an order on behalf of an authenticated user,
I want to include an optional `discount_code` in the order-creation request,
so that the order total is reduced by the code's percentage and the discounted amount is returned in the response.

## Acceptance Criteria

1. `POST /orders` accepts an optional `discount_code` string field. Omitting it behaves identically to today (regression: existing tests pass unchanged).
2. When `discount_code` is present and matches a `DiscountCode` row, the response includes `discount_code` (the code string) and `discounted_total` (integer cents = `round(total * (1 - percentage / 100))`).
3. A 5 % code on any order produces `discounted_total = round(total * 0.95)`.
4. A 10 % code on any order produces `discounted_total = round(total * 0.90)`.
5. A 20 % code on any order produces `discounted_total = round(total * 0.80)`.
6. An unknown `discount_code` value returns HTTP 422 with a descriptive error detail.
7. `GET /orders/{id}` for an order created with a code returns the same `discount_code` and `discounted_total` values as the creation response.
8. `GET /orders/{id}` for an order created without a code returns `discount_code: null` and `discounted_total: null`.
9. All seven new tests in `tests/test_discount.py` pass. All pre-existing tests pass.

## Tasks / Subtasks

- [x] Update `OrderCreate` Pydantic schema in `src/api/routes/orders.py` (AC: 1)
  - [x] Add `discount_code: str | None = None` field
- [x] Update `OrderOut` Pydantic schema in `src/api/routes/orders.py` (AC: 1, 7, 8)
  - [x] Add `discount_code: str | None = None`
  - [x] Add `discounted_total: int | None = None`
- [x] Add discount lookup + computation to `create_order` route (AC: 2–6)
  - [x] Import `DiscountCode` from `api.models` at top of file
  - [x] After the item-loop that computes `total`, before `db.commit()`: if `payload.discount_code` is not None, query `DiscountCode` by `code`; raise `HTTPException(status_code=422, ...)` if not found; compute `discounted_total = round(total * (1 - dc.percentage / 100))`
  - [x] Assign `order.discount_code = discount_code_str` and `order.discounted_total = discounted_total` before commit
- [x] Update `OrderOut(...)` construction in `create_order` to pass new fields (AC: 2, 8)
- [x] Update `OrderOut(...)` construction in `get_order` to pass new fields (AC: 7, 8)
- [x] Add `db` fixture to `tests/conftest.py` (needed to seed `DiscountCode` rows in tests)
  - [x] Fixture takes `db_engine`, yields a `Session`, closes on teardown
  - [x] Does not alter any existing fixture
- [x] Write `tests/test_discount.py` with the following tests (AC: 3–9):
  - [x] `test_discount_5_percent` — seed 5 % code, create order, assert `discounted_total == round(total * 0.95)`
  - [x] `test_discount_10_percent` — seed 10 % code, assert correct value
  - [x] `test_discount_20_percent` — seed 20 % code, assert correct value
  - [x] `test_unknown_discount_code_returns_422` — unknown code → HTTP 422, detail contains the code string
  - [x] `test_no_discount_code_regression` — no `discount_code` field → HTTP 201, `total` unchanged from item sum
  - [x] `test_no_discount_fields_are_null` — no code → response has `discount_code: null`, `discounted_total: null`
  - [x] `test_discount_visible_on_get_order` — GET after POST returns same `discount_code` + `discounted_total`
- [x] Run full `pytest` suite and confirm all tests green (AC: 9)

## Dev Notes

**Exact code shape for the discount block (place after total computed, before `db.commit()`):**

```python
discount_code_str: str | None = None
discounted_total: int | None = None

if payload.discount_code is not None:
    dc = db.query(DiscountCode).filter(DiscountCode.code == payload.discount_code).one_or_none()
    if dc is None:
        raise HTTPException(status_code=422, detail=f"unknown discount code '{payload.discount_code}'")
    discount_code_str = dc.code
    discounted_total = round(total * (1 - dc.percentage / 100))

order.total = total
order.discount_code = discount_code_str
order.discounted_total = discounted_total
```

**Critical conventions to follow (from convention sweep):**

- **Money is always integer cents.** `discounted_total` is computed from `total` (already in cents) using `round()` — the same rounding as `_to_cents()`. Do NOT compute from dollars. Do NOT store a float.
- **`round()` not `int(x * factor)`.** The existing `add_item_inline` helper uses `int(unit_price_dollars * 100)` without `round()` — that is a latent bug. Do not copy it. Use `round(total * (1 - dc.percentage / 100))` exactly as specified.
- **`discounted_total` is never stored as float.** `round()` in Python returns an `int` when given an `int` argument, so `round(int * float)` returns `int`. No explicit `int()` cast needed, but verify.
- **Both `create_order` and `get_order` build `OrderOut(...)` manually** — there is no `from_attributes` on `OrderOut`. Both call sites must be updated to pass the new fields. Missing either one means `GET /orders/{id}` will return nulls even for discounted orders, failing AC 7.
- **`created_at` format is `"%Y-%d-%m"` (day-month swapped, NOT ISO 8601).** Do not touch the date formatting. Do not "fix" it.
- **Test helper for seeding discount codes:**

```python
# In tests/test_discount.py
def _seed_code(db, code: str, percentage: int):
    from api.models import DiscountCode
    dc = DiscountCode(code=code, percentage=percentage)
    db.add(dc)
    db.commit()
```

- **Test helper for creating users** — copy the pattern from `test_orders.py`:

```python
def _make_user(client, email="u@example.com", name="U"):
    r = client.post("/users", json={"email": email, "name": name})
    assert r.status_code == 201
    return r.json()
```

- **Test fixture for `db`** — both `client` and `db` must take `db_engine` so they share the same in-memory SQLite. Tests that need to seed rows AND make HTTP calls take both fixtures:

```python
# tests/conftest.py — add only this, do not change existing fixtures
@pytest.fixture
def db(db_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()
```

- **`autoflush=False` on the test session.** After `_seed_code(db, ...)`, `db.commit()` is called inside `_seed_code` — data is visible to HTTP calls through the `client` fixture because both use the same `db_engine`.

**What this story does NOT touch:**
- `src/api/models.py` — completed in Story 1.1; import `DiscountCode` but do not modify the model
- `src/api/deps.py`, `src/api/main.py`, `src/api/utils/` — untouched
- `tests/test_orders.py`, `tests/test_users.py`, `tests/test_dates.py` — untouched; they must pass as-is

**Dependency:** Story 1.1 must be complete before this story starts. `DiscountCode` model and the `Order` nullable columns must exist in `models.py`.

### Project Structure Notes

- Files changed: `src/api/routes/orders.py`, `tests/conftest.py` (one fixture added), `tests/test_discount.py` (new file)
- No new modules, no new routers, no changes to `main.py`

### References

- Architecture doc: `_bmad-output/planning-artifacts/architecture.md` — §4 Schema Changes, §5 Route Logic, §6 Test Strategy
- PRD: `_bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md` — FR-1, FR-2, FR-3
- Convention sweep: shared session in tests, `_to_cents()` rounding pattern, `%Y-%d-%m` date format

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Added `discount_code: str | None = None` to `OrderCreate`; added `discount_code` and `discounted_total` nullable fields to `OrderOut`.
- Discount lookup block placed in `create_order` after item-loop, before `db.commit()`. Unknown code raises HTTP 422. `round()` used for computation — consistent with `_to_cents()` pattern.
- Both `create_order` and `get_order` `OrderOut(...)` constructions updated to pass `discount_code` and `discounted_total`.
- Added `db` fixture to `conftest.py` (takes `db_engine`, yields session) without altering existing fixtures.
- New `tests/test_discount.py` with 7 tests covering all three percentages, unknown code, regression (no code), null fields, and GET round-trip.
- 18/18 tests pass (11 pre-existing + 7 new). No regressions.

### File List

- src/api/routes/orders.py
- tests/conftest.py
- tests/test_discount.py
