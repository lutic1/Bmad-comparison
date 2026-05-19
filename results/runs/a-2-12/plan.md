# Add `POST /orders/{order_id}/refund`

## Context

The orders service currently supports creating and reading orders, but has no
way to refund one. The task adds an authenticated endpoint that lets the
order's owner refund an order within 30 days of creation, marks the order as
refunded, and returns a refund record.

There is no existing `Refund` model or refund-related code in the repo. The
30-day rule and "return the refund record" requirement imply we should
persist refunds (not just flip a flag on the order), so a sibling table is
the natural fit.

## Approach

### 1. Model changes — `src/api/models.py`

- Add `refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)` to `Order`. This is the "mark as refunded" field; presence indicates the order has been refunded and blocks repeat refunds.
- Add a new `Refund` model:
  - `id: int` PK
  - `order_id: int` FK → `orders.id`, unique (one refund per order)
  - `amount: int` (cents — snapshot of `order.total` at refund time, so refund records remain meaningful even if the order is later mutated)
  - `created_at: datetime` defaulting to `datetime.utcnow`
  - `order: Mapped[Order] = relationship()` back-reference (one-directional is fine; matches the existing minimalism)

Schema is auto-created from `Base.metadata` at startup and `app.db` is wiped between runs (per CLAUDE.md), so no migration needed.

### 2. Route — `src/api/routes/orders.py`

Add a `POST /orders/{order_id}/refund` handler alongside the existing routes. Follow the established patterns exactly (small inline business logic, `db.add → db.commit → db.refresh`, `from_attributes=True` Pydantic response model, `strftime("%Y-%d-%m")` for datetime serialization — note the quirky non-ISO format already used in `create_order` / `get_order`).

Pydantic response model:
```python
class RefundOut(BaseModel):
    id: int
    order_id: int
    amount: int
    created_at: str
```

Handler logic (in order):
1. `order = db.get(Order, order_id)` → 404 `"order not found"` if `None`.
2. `if order.user_id != user.id:` → 403 `"forbidden"`. (Match existing wording.)
3. `if order.refunded_at is not None:` → 400 `"order already refunded"`.
4. `if datetime.utcnow() - order.created_at > timedelta(days=30):` → 400 `"refund window expired"`.
5. Create `Refund(order_id=order.id, amount=order.total)`, `db.add(refund)`, set `order.refunded_at = datetime.utcnow()`, `db.commit()`, `db.refresh(refund)`.
6. Return `RefundOut(...)` with `created_at=refund.created_at.strftime("%Y-%d-%m")`.

Import `timedelta` from `datetime` and `Refund` from `api.models`. Use `status_code=201` to match `create_order`.

### 3. Tests — `tests/test_orders.py`

Add tests at the bottom of the existing file. Reuse the `client` fixture and `_make_user` helper. For the 30-day window test, also use the `db_engine` fixture to backdate an order's `created_at` directly via SQLAlchemy (the `client` fixture binds the test session to that same engine, so writes are visible to subsequent HTTP calls).

Cases to cover:
- `test_refund_requires_auth` — POST without `X-User-Id` → 401.
- `test_refund_unknown_order_returns_404` — auth'd POST to nonexistent id → 404.
- `test_refund_forbidden_for_other_user` — non-owner → 403.
- `test_refund_happy_path` — owner refunds a fresh order → 201; response contains `id`, `order_id`, `amount` equal to the order total in cents, `created_at` string. Follow-up `GET /orders/{id}` still works (sanity check that the order row survived).
- `test_refund_outside_30_day_window` — create order, then via a session bound to `db_engine` set `order.created_at = datetime.utcnow() - timedelta(days=31)`, commit; POST → 400 `"refund window expired"`.
- `test_refund_already_refunded` — refund once (201), refund again → 400 `"order already refunded"`.

The backdating test will need `from datetime import datetime, timedelta` and `from sqlalchemy.orm import sessionmaker` (or just open a `Session` against `db_engine`) plus `from api.models import Order`. Keep it inline in the single test that needs it rather than adding a fixture.

## Critical files

- `src/api/models.py` — add `Order.refunded_at`, add `Refund` model.
- `src/api/routes/orders.py` — add `RefundOut` + `refund_order` handler.
- `tests/test_orders.py` — add the six tests above.

No changes needed to `src/api/main.py` (the orders router is already mounted), `deps.py`, or `pyproject.toml`.

## Reused utilities / patterns

- `api.deps.get_current_user` and `api.deps.get_db` — exact same dependency pair as every other protected route.
- `HTTPException(status_code=…, detail=…)` — match the wording style ("order not found", "forbidden").
- `db.get(Order, order_id)` — same lookup pattern as `get_order`.
- `strftime("%Y-%d-%m")` — same datetime serialization the existing routes use (matches `test_dates.py` expectations).
- `_make_user` test helper at the top of `tests/test_orders.py`.

## Verification

1. `cd /Users/luisticas/bmad-demo/target && pytest tests/test_orders.py -v` — all old tests still pass, new refund tests pass.
2. `pytest` — full suite green (CLAUDE.md: do not commit if pytest is failing).
3. Smoke check via FastAPI's interactive docs (optional): start the app, create a user + order, POST `/orders/{id}/refund` with the `X-User-Id` header, verify 201 and JSON shape.
