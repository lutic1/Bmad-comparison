from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from api.models import DiscountCode, Order, User
from api.routes.orders import OrderItemOut, OrderOut

router = APIRouter(prefix="/orders", tags=["discounts"])


class DiscountCodeApply(BaseModel):
    code: str


def _to_order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        user_id=order.user_id,
        total=order.total,
        discount_code=order.discount_code.code if order.discount_code else None,
        discount_amount_cents=order.discount_amount_cents,
        created_at=order.created_at.strftime("%Y-%d-%m"),
        items=[
            OrderItemOut(sku=i.sku, quantity=i.quantity, unit_price=i.unit_price)
            for i in order.items
        ],
    )


@router.post("/{order_id}/discount-code", response_model=OrderOut)
def apply_discount_code(
    order_id: int,
    payload: DiscountCodeApply,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderOut:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="forbidden")

    discount = db.query(DiscountCode).filter_by(code=payload.code.upper()).first()
    if discount is None:
        raise HTTPException(status_code=422, detail="invalid discount code")

    if order.discount_code_id is not None:
        order.total += order.discount_amount_cents

    discount_amount = round(order.total * discount.discount_percent / 100)
    order.total = max(0, order.total - discount_amount)
    order.discount_code_id = discount.id
    order.discount_amount_cents = discount_amount

    db.commit()
    db.refresh(order)

    return _to_order_out(order)


@router.delete("/{order_id}/discount-code", response_model=OrderOut)
def remove_discount_code(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderOut:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="forbidden")
    if order.discount_code_id is None:
        raise HTTPException(status_code=400, detail="no discount code applied")

    order.total += order.discount_amount_cents
    order.discount_code_id = None
    order.discount_amount_cents = 0

    db.commit()
    db.refresh(order)

    return _to_order_out(order)
