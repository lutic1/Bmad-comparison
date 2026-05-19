# Plan: `POST /orders/{order_id}/refund`

## Context

The service has order creation/retrieval but no way to refund. We need an authenticated endpoint that refunds an order (full amount) within 30 days of creation, marks the order refunded so it can't be refunded twice, and returns the persisted refund record. Refund metadata lives in its own table (so we keep an auditable history), and the `Order` gets a `refunded_at` timestamp so the "already refunded" check is a column read.

## Design decisions

- **Full refund only.** Spec says "mark the order as refunded" — single refund per order, amount = `order.total`. No partial-refund parameter.
- **New `Refund` model** (not just a flag on `Order`) — gives us `id` and `created_at` to return as the refund record.
- **`Order.refunded_at: datetime | None`** — single source of truth for "is refunded". Prevents double-refunds with one column check.
- **30-day window**: `datetime.utcnow() - order.created_at > timedelta(days=30)` → 400. Use `utcnow()` to match the model's `default=datetime.utcnow`.
- **Status codes** follow existing patterns: 401 missing auth, 403 not owner, 404 order missing, 400 outside window, 409 already refunded, 201 on create.

## Files to modify

### `src/api/models.py`

1. Add `refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)` to `Order`.
2. Add `Refund` model:
   ```python
   class Refund(Base):
       __tablename__ = "refunds"
       id: Mapped[int] = mapped_column(Integer, primary_key=True)
       order_id: Mapped[int] = mapped_column(
           ForeignKey("orders.id"), nullable=False, unique=True
       )
       amount: Mapped[int] = mapped_column(Integer, nullable=False)  # cents
       created_at: Mapped[datetime] = mapped_column(
           DateTime, default=datetime.utcnow, nullable=False
       )
       order: Mapped[Order] = relationship()
   ```
   `unique=True` on `order_id` belt-and-suspenders against double refunds.

No migration needed — CLAUDE.md says the operator wipes `app.db` between runs.

### `src/api/routes/orders.py`

1. Import `timedelta` from `datetime`, and `Refund` from `api.models`.
2. Add `RefundOut` Pydantic model:
   ```python
   class RefundOut(BaseModel):
       id: int
       order_id: int
       amount: int
       created_at: str
   ```
3. Add the route (uses the existing router with `prefix="/orders"`):
   ```python
   @router.post("/{order_id}/refund", response_model=RefundOut, status_code=201)
   def refund_order(
       order_id: int,
       db: Session = Depends(get_db),
       user: User = Depends(get_current_user),
   ) -> RefundOut:
       order = db.get(Order, order_id)
       if order is None:
           raise HTTPException(status_code=404, detail="order not found")
       if order.user_id != user.id:
           raise HTTPException(status_code=403, detail="forbidden")
       if order.refunded_at is not None:
           raise HTTPException(status_code=409, detail="order already refunded")
       if datetime.utcnow() - order.created_at > timedelta(days=30):
           raise HTTPException(status_code=400, detail="refund window expired")

       refund = Refund(order_id=order.id, amount=order.total)
       order.refunded_at = datetime.utcnow()
       db.add(refund)
       db.commit()
       db.refresh(refund)

       return RefundOut(
           id=refund.id,
           order_id=refund.order_id,
           amount=refund.amount,
           created_at=refund.created_at.strftime("%Y-%d-%m"),
       )
   ```
   Reuses existing patterns: `get_current_user` for auth, the same ownership check as `get_order`, the existing `"%Y-%d-%m"` date format used elsewhere in this file.

### `tests/test_orders.py` (append)

Cover one behaviour per test, following the file's existing `_make_user` helper and TestClient style:

1. `test_refund_requires_auth` — POST without `X-User-Id` → 401.
2. `test_refund_order_not_found` — POST `/orders/9999/refund` → 404.
3. `test_refund_forbidden_for_other_user` — owner creates order, other user attempts refund → 403.
4. `test_refund_success` — owner refunds → 201, response has `order_id`, `amount == order.total`, integer `id`, `created_at` string.
5. `test_refund_outside_window_rejected` — create order, manually rewrite `created_at` to 31 days ago in the DB, refund → 400. Will need DB access via a small fixture or a direct `SessionLocal` patch; simplest is to import the test session via `app.dependency_overrides[deps.get_db]` re-use or query inside the test using a fresh session against the same `db_engine` fixture (extend `conftest.py` only if needed — prefer using the existing `db_engine` fixture by adding it as a test argument).
6. `test_refund_twice_rejected` — refund once (201), refund again → 409.

For test #5, the cleanest path is to add `db_engine` as a parameter alongside `client` and use a short-lived `Session(db_engine)` block to update `created_at`. No `conftest.py` changes required — `db_engine` is already a fixture.

## Critical files

- `/Users/luisticas/bmad-demo/target/src/api/models.py` — add `Order.refunded_at`, add `Refund`.
- `/Users/luisticas/bmad-demo/target/src/api/routes/orders.py` — add `RefundOut`, add route.
- `/Users/luisticas/bmad-demo/target/tests/test_orders.py` — append 6 tests.

## Verification

1. `pytest tests/test_orders.py -v` — all new tests pass, existing tests still pass.
2. `pytest` — full suite green (CLAUDE.md: don't commit if pytest is failing).
3. Manual smoke (optional): `uvicorn api.main:app`, create a user, create an order, POST to `/orders/{id}/refund` with `X-User-Id` header, verify 201 + refund body; repeat to verify 409.
