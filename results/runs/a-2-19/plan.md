# Plan: POST /orders/{order_id}/refund

## Context
The service has users and orders but no refund capability. This adds a refund endpoint that authenticates the caller, validates ownership and the 30-day window, persists the refund, and returns it.

## Files to modify

| File | Change |
|------|--------|
| `src/api/models.py` | Add `refunded_at` to `Order`; add `Refund` model |
| `src/api/routes/orders.py` | Add `RefundOut` Pydantic model + endpoint |
| `tests/test_orders.py` | Add refund tests |

---

## 1. `src/api/models.py`

Add `refunded_at: Mapped[datetime | None]` (nullable) to `Order` and a `refunds` back-reference.

Add a `Refund` table:

```python
class Refund(Base):
    __tablename__ = "refunds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # cents
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    order: Mapped["Order"] = relationship(back_populates="refunds")
```

Add to `Order`:
```python
refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
refunds: Mapped[list["Refund"]] = relationship(back_populates="order", cascade="all, delete-orphan")
```

---

## 2. `src/api/routes/orders.py`

### New Pydantic response model
```python
class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    amount: int
    created_at: datetime
```

### New endpoint
```python
@router.post("/{order_id}/refund", response_model=RefundOut, status_code=201)
def refund_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Refund:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="not your order")
    if order.refunded_at is not None:
        raise HTTPException(status_code=409, detail="order already refunded")
    if (datetime.utcnow() - order.created_at).days > 30:
        raise HTTPException(status_code=400, detail="refund window expired")
    order.refunded_at = datetime.utcnow()
    refund = Refund(order_id=order.id, amount=order.total)
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return refund
```

---

## 3. `tests/test_orders.py`

New tests (all use existing `client` fixture + `_make_user` helper):

- `test_refund_requires_auth` — no header → 401
- `test_refund_order_not_found` — unknown order_id → 404
- `test_refund_wrong_user` — other user's order → 403
- `test_refund_already_refunded` — second call → 409
- `test_refund_window_expired` — directly update `order.created_at` to 31 days ago via DB, then call → 400
- `test_refund_success` — happy path → 201 with `id`, `order_id`, `amount` (in cents), `created_at`

For the expired-window test: create the order normally, then use a raw DB session (via `db_engine` fixture) to backdate `created_at` before calling the endpoint.

---

## Verification

```bash
pytest tests/test_orders.py -q
pytest -q   # full suite must stay green
```
