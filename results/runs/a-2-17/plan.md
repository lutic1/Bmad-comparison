# Plan: POST /orders/{order_id}/refund

## Context

The service has users and orders but no refund capability. We need a refund endpoint that validates ownership and a 30-day window, then creates a persistent refund record.

## Files to Modify

- `src/api/models.py` — add `Refund` model and `refund` relationship to `Order`
- `src/api/routes/orders.py` — add `RefundOut` schema and the new endpoint

## Files to Create

- `tests/test_refunds.py` — test all behaviors

---

## Step 1: `src/api/models.py`

Add a `Refund` model (new table, `order_id` unique so one refund per order):

```python
class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    refunded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="refund")
```

Add to `Order`:
```python
refund: Mapped["Refund | None"] = relationship(back_populates="order", uselist=False)
```

The `order.refund is not None` check replaces any separate boolean flag — the relationship IS the mark.

## Step 2: `src/api/routes/orders.py`

**Imports**: add `Refund` to the `from api.models import ...` line.

**New schema** (after existing schemas):
```python
class RefundOut(BaseModel):
    id: int
    order_id: int
    amount: int
    refunded_at: str
```

**New endpoint**:
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
    if order.refund is not None:
        raise HTTPException(status_code=409, detail="order already refunded")
    if (datetime.utcnow() - order.created_at).days > 30:
        raise HTTPException(status_code=422, detail="refund window has expired")

    refund = Refund(order_id=order.id, amount=order.total)
    db.add(refund)
    db.commit()
    db.refresh(refund)

    return RefundOut(
        id=refund.id,
        order_id=refund.order_id,
        amount=refund.amount,
        refunded_at=refund.refunded_at.isoformat(),
    )
```

## Step 3: `tests/test_refunds.py`

Use the existing `client` fixture from `conftest.py`. Helper creates a user + order. Tests:

| Test | Expected |
|---|---|
| successful refund | 201, returns refund record with correct fields |
| missing X-User-Id header | 401 |
| order not found | 404 |
| order belongs to different user | 403 |
| already refunded | 409 |
| order older than 30 days | 422 |

For the 30-day test: create an order then manually backdate `created_at` via the db session before calling the endpoint.

## Verification

```bash
cd /Users/luisticas/bmad-demo/target
pytest tests/test_refunds.py -v
pytest -q  # full suite should still pass
```
