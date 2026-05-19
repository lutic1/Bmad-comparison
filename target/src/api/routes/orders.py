from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
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
    created_at: str
    items: list[OrderItemOut]


class RefundOut(BaseModel):
    order_id: int
    refunded_at: str


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderOut:
    if not payload.items:
        raise HTTPException(status_code=400, detail="order must have at least one item")

    order = Order(user_id=user.id, total=0)
    db.add(order)
    db.flush()

    total = 0
    for item in payload.items:
        unit_price_cents = _to_cents(item.unit_price)
        line = OrderItem(
            order_id=order.id,
            sku=item.sku,
            quantity=item.quantity,
            unit_price=unit_price_cents,
        )
        db.add(line)
        total += unit_price_cents * item.quantity

    order.total = total
    db.commit()
    db.refresh(order)

    return OrderOut(
        id=order.id,
        user_id=order.user_id,
        total=order.total,
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
        created_at=order.created_at.strftime("%Y-%d-%m"),
        items=[
            OrderItemOut(sku=i.sku, quantity=i.quantity, unit_price=i.unit_price)
            for i in order.items
        ],
    )


@router.post("/{order_id}/refund", response_model=RefundOut, status_code=200)
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
    age = datetime.utcnow() - order.created_at
    if age.days > 30:
        raise HTTPException(status_code=400, detail="refund window expired")
    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return RefundOut(
        order_id=order.id,
        refunded_at=order.refunded_at.strftime("%Y-%d-%m"),
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
