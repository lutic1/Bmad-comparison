# Plan: POST /orders/{order_id}/refund

## Context

The orders service needs a refund endpoint. Orders can be refunded within 30 days of creation by the owning user. A separate `Refund` model tracks refund records (satisfying "return the refund record"), and a unique constraint on `order_id` prevents double-refunds at the DB level.

---

## Files to modify

### 1. `src/api/models.py`

Add a `Refund` model and a back-reference on `Order`:

```python
# Add to Order:
refund: Mapped["Refund | None"] = relationship(back_populates="order", uselist=False)

# New model:
class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="refund")
```

### 2. `src/api/routes/orders.py`

- Add `timedelta` to the `from datetime import ...` import.
- Import `Refund` from `api.models`.
- Add `RefundOut` Pydantic schema.
- Add the route.

```python
class RefundOut(BaseModel):
    id: int
    order_id: int
    created_at: str

@router.post("/{order_id}/refund", response_model=RefundOut, status_code=201)
def create_refund(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RefundOut:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="forbidden")
    if order.refund is not None:
        raise HTTPException(status_code=409, detail="order already refunded")
    if datetime.utcnow() - order.created_at > timedelta(days=30):
        raise HTTPException(status_code=400, detail="refund window has closed")

    refund = Refund(order_id=order.id)
    db.add(refund)
    db.commit()
    db.refresh(refund)

    return RefundOut(
        id=refund.id,
        order_id=refund.order_id,
        created_at=refund.created_at.strftime("%Y-%d-%m"),
    )
```

### 3. `tests/test_refund.py` (new file)

Helper fixtures + 6 tests:

| Test | Expected |
|---|---|
| `test_refund_requires_auth` | 401 — no X-User-Id header |
| `test_refund_order_not_found` | 404 — unknown order_id |
| `test_refund_forbidden_for_other_user` | 403 — wrong user |
| `test_refund_success` | 201 — returns RefundOut with `id`, `order_id`, `created_at` |
| `test_refund_already_refunded` | 409 — second POST on same order |
| `test_refund_outside_window` | 400 — order.created_at pushed 31 days back via direct DB session |

For `test_refund_outside_window`, add a local `db` fixture that shares the `db_engine` fixture to directly update `order.created_at`:

```python
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()
```

---

## Verification

```bash
cd /Users/luisticas/bmad-demo/target
pytest tests/test_refund.py -v
pytest  # full suite must stay green
```
