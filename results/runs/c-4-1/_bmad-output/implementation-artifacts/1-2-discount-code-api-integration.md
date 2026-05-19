# Story 1.2: Discount Code API Integration

Status: done

## Story

As an API consumer placing an order,
I want to supply an optional `discount_code` field on `POST /orders` that is validated against the `discount_codes` table and reduces my order total by the associated percentage,
so that the discounted total is persisted and returned in the response, and invalid codes are rejected clearly before any order is created.

## Acceptance Criteria

1. `OrderCreate` in `src/api/routes/orders.py` accepts an optional field `discount_code: str | None = None`. Omitting it (or passing `null`) leaves the existing order-creation flow completely unchanged.
2. When `discount_code` is provided, `create_order` normalises it with `.strip().upper()`, queries `DiscountCode` for an exact match, and raises `HTTPException(status_code=422, detail=f"invalid discount code: {payload.discount_code!r}")` if no match is found. No order row is created on rejection.
3. When a valid code is found, `order.total = round(original_total_cents * (1 - discount_pct / 100))`. `order.discount_code` is set to the stored (UPPER CASE) code string; `order.discount_pct` is set to the integer percentage. Both fields persist to the DB.
4. `OrderOut` in `src/api/routes/orders.py` adds `discount_code: str | None = None` and `discount_pct: int | None = None`. Both `create_order` and `get_order` thread these fields explicitly through every `OrderOut(...)` constructor call.
5. `GET /orders/{id}` returns the correct `discount_code` and `discount_pct` for a previously discounted order (and `null` for both fields on a non-discounted order).
6. All 7 tests listed below are added to `tests/test_orders.py` and pass. All pre-existing tests continue to pass.

### Tests required (AC: 6)

| Test function | Fixture(s) | Scenario | Key assertion |
|---|---|---|---|
| `test_discount_no_code_regression` | `client` | POST without `discount_code` | `total` == 1998, `discount_code` is null, `discount_pct` is null |
| `test_discount_5pct` | `client, discount_codes` | SAVE5 on 2×$9.99 | `total == 1898` (`round(1998 * 0.95)`), `discount_pct == 5` |
| `test_discount_10pct` | `client, discount_codes` | SAVE10 on 2×$9.99 | `total == 1798` (`round(1998 * 0.90)`), `discount_pct == 10` |
| `test_discount_20pct` | `client, discount_codes` | SAVE20 on 2×$9.99 | `total == 1598` (`round(1998 * 0.80)`), `discount_pct == 20` |
| `test_discount_unknown_code` | `client, discount_codes` | `discount_code: "BOGUS"` | HTTP 422; zero orders in DB |
| `test_discount_case_insensitive` | `client, discount_codes` | `discount_code: "save10"` | HTTP 201, `discount_pct == 10` |
| `test_discount_fields_on_get_order` | `client, discount_codes` | GET after discounted POST | `discount_code == "SAVE10"`, `discount_pct == 10` |

## Tasks / Subtasks

- [x] Extend `OrderCreate` with optional `discount_code` field (AC: 1)
  - [x] Add `discount_code: str | None = None` after the `items` field
- [x] Extend `OrderOut` with two nullable fields (AC: 4)
  - [x] Add `discount_code: str | None = None` and `discount_pct: int | None = None` at the end of the class
  - [x] `OrderOut` does NOT use `from_attributes = True` — both fields must be passed explicitly in every constructor call
- [x] Update `create_order` handler (AC: 2, 3)
  - [x] Add `from api.models import DiscountCode, Order, OrderItem, User` (add `DiscountCode` to existing import)
  - [x] Before the `Order(...)` insert: if `payload.discount_code` is not None, normalise → query → raise 422 on miss; record `discount_pct` and `applied_code`
  - [x] After accumulating `total`: if discount applies, `total = round(total * (1 - discount_pct / 100))`
  - [x] Set `order.discount_code = applied_code` and `order.discount_pct = discount_pct` before `db.commit()`
  - [x] Update the `return OrderOut(...)` call to include `discount_code=order.discount_code, discount_pct=order.discount_pct`
- [x] Update `get_order` handler (AC: 4, 5)
  - [x] Update its `return OrderOut(...)` call to include `discount_code=order.discount_code, discount_pct=order.discount_pct`
  - [x] No other logic change needed — fields are already on the ORM object
- [x] Add 7 tests to `tests/test_orders.py` (AC: 6)
  - [x] Follow the `_make_user(client, email=..., name=...)` helper pattern for user creation; use unique emails
  - [x] Tests using discount codes declare `discount_codes` as a fixture parameter (seeds SAVE5/10/20 via the `db` fixture from Story 1.1)
  - [x] Use `round(1998 * 0.X)` directly in assertions — do not hardcode magic numbers without the formula as a comment
- [x] Run `pytest` and confirm all tests pass (AC: 6)

## Dev Notes

**Critical conventions — must read before writing code:**

- **`OrderOut` is manually constructed — never auto-mapped from ORM.** `OrderItemOut` has `from_attributes = True`; `OrderOut` does not. Both `create_order` and `get_order` build `OrderOut(id=..., user_id=..., ...)` field-by-field. The two new fields must appear in both call sites.
- **Money is always integer cents.** `total`, `unit_price` — all `Integer`. The discount computation operates entirely on integer cents: `round(total_cents * (1 - pct/100))`. No floats reach the DB.
- **`round()` not `int(round(...))`.** The existing `_to_cents` uses `int(round(...))` for dollar→cent conversion. For the discount computation, use bare `round()` — the result is already in cents and Python 3's `round()` returns an `int` when given an `int * float`.
- **Date format is `%Y-%d-%m` (day/month swapped) — do not fix it.** Both `create_order` and `get_order` use `order.created_at.strftime("%Y-%d-%m")`. Preserve this in both handlers when updating the `OrderOut(...)` constructor.
- **`autoflush=False`.** The existing pattern is: `Order(total=0)` → `db.add` → `db.flush()` (to get PK) → add items → set final total → `db.commit()` → `db.refresh()`. The discount validation and computation fit in this flow: validate before `Order(...)` insert; compute after item accumulation; assign to `order` before commit.
- **HTTP 422 for invalid code** — consistent with FastAPI's validation error shape. The detail string must reference the submitted code: `f"invalid discount code: {payload.discount_code!r}"`.
- **Test emails must be unique per test.** `_make_user` defaults to `u@example.com`; tests that create users must pass explicit emails to avoid 409 conflicts.
- **`discount_codes` fixture from Story 1.1 seeds SAVE5/SAVE10/SAVE20.** Any test using discount codes declares `discount_codes` as a parameter — pytest injects it automatically.
- **Do not touch `adjust_total`, `add_item_inline`, or `_format_created_at`** — dead code at bottom of `orders.py`; ignore completely.

### Prerequisite

Story 1.1 must be complete. This story assumes `DiscountCode` model exists in `src/api/models.py`, the `Order` model already has `discount_code` and `discount_pct` columns, and `tests/conftest.py` already has `db` and `discount_codes` fixtures.

### Project Structure Notes

- `src/api/routes/orders.py` — extend in-place; no new route files
- `tests/test_orders.py` — append 7 new test functions at the bottom

### References

- Architecture §3 API Changes [Source: `_bmad-output/planning-artifacts/architecture.md#3-api-changes`]
- Architecture §5 Test Coverage Plan [Source: `_bmad-output/planning-artifacts/architecture.md#5-test-coverage-plan`]
- Architecture §1 Guiding Decisions [Source: `_bmad-output/planning-artifacts/architecture.md#1-guiding-decisions`]
- PRD FR-2 through FR-5 [Source: `_bmad-output/planning-artifacts/prds/prd-target-2026-05-18/prd.md`]
- Convention sweep findings: `OrderOut` manual construction, cents-only arithmetic, date format lock

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `DiscountCode` to import in `src/api/routes/orders.py`
- `OrderCreate`: added `discount_code: str | None = None`
- `OrderOut`: added `discount_code: str | None = None` and `discount_pct: int | None = None`
- `create_order`: validates code before order insert (normalise → query → 422 on miss); applies `round(total * (1 - pct/100))` after item accumulation; sets both fields on order; threads through `OrderOut` constructor
- `get_order`: threads `discount_code` and `discount_pct` through `OrderOut` constructor
- 7 new tests appended to `tests/test_orders.py`; shared item fixture `_ITEMS_2x999` avoids magic numbers inline
- 18/18 tests pass; 0 regressions

### File List

- `src/api/routes/orders.py`
- `tests/test_orders.py`
