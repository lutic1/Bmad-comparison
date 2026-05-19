from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from api.discounts import InvalidDiscountCode, apply_discount, resolve_percent
from api.models import Order, OrderItem, User

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_cents(dollars: float) -> int:
    return int(round(dollars * 100))


class OrderItemIn(BaseModel):
    sku: str
    quantity: int
    unit_price: float


class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    discount_code: str | None = None


class OrderItemOut(BaseModel):
    sku: str
    quantity: int
    unit_price: int

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    discount_code: str | None
    discount_percent: int | None
    discount_cents: int | None
    created_at: str
    items: list[OrderItemOut]


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderOut:
    if not payload.items:
        raise HTTPException(status_code=400, detail="order must have at least one item")

    # Validate discount BEFORE writing anything so an invalid code leaves zero rows.
    discount_code: str | None = None
    discount_percent: int | None = None
    if payload.discount_code is not None:
        try:
            discount_code, discount_percent = resolve_percent(payload.discount_code)
        except InvalidDiscountCode:
            raise HTTPException(status_code=400, detail="invalid discount code")

    order = Order(user_id=user.id, total=0)
    db.add(order)
    db.flush()

    subtotal = 0
    for item in payload.items:
        unit_price_cents = _to_cents(item.unit_price)
        line = OrderItem(
            order_id=order.id,
            sku=item.sku,
            quantity=item.quantity,
            unit_price=unit_price_cents,
        )
        db.add(line)
        subtotal += unit_price_cents * item.quantity

    if discount_percent is not None:
        total, discount_cents = apply_discount(subtotal, discount_percent)
    else:
        total, discount_cents = subtotal, None

    order.total = total
    order.discount_code = discount_code
    order.discount_percent = discount_percent
    order.discount_cents = discount_cents
    db.commit()
    db.refresh(order)

    return OrderOut(
        id=order.id,
        user_id=order.user_id,
        total=order.total,
        discount_code=order.discount_code,
        discount_percent=order.discount_percent,
        discount_cents=order.discount_cents,
        created_at=order.created_at.strftime("%Y-%d-%m"),
        items=[
            OrderItemOut(sku=i.sku, quantity=i.quantity, unit_price=i.unit_price)
            for i in order.items
        ],
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderOut:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="forbidden")

    return OrderOut(
        id=order.id,
        user_id=order.user_id,
        total=order.total,
        discount_code=order.discount_code,
        discount_percent=order.discount_percent,
        discount_cents=order.discount_cents,
        created_at=order.created_at.strftime("%Y-%d-%m"),
        items=[
            OrderItemOut(sku=i.sku, quantity=i.quantity, unit_price=i.unit_price)
            for i in order.items
        ],
    )


def adjust_total(order: Order, delta_cents: int) -> None:
    order.total = max(0, order.total + delta_cents)


def add_item_inline(order: Order, sku: str, quantity: int, unit_price_dollars: float) -> None:
    unit_price_cents = int(unit_price_dollars * 100)
    order.items.append(
        OrderItem(
            order_id=order.id,
            sku=sku,
            quantity=quantity,
            unit_price=unit_price_cents,
        )
    )
    order.total += unit_price_cents * quantity


def _format_created_at(dt: datetime) -> str:
    return dt.strftime("%Y-%d-%m")
