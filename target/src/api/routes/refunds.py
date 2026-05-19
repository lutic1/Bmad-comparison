from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from api.models import Order, Refund, User

router = APIRouter(prefix="/orders", tags=["refunds"])

REFUND_WINDOW = timedelta(days=30)


class RefundOut(BaseModel):
    id: int
    order_id: int
    amount: int
    created_at: str


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
    if datetime.utcnow() - order.created_at > REFUND_WINDOW:
        raise HTTPException(status_code=400, detail="refund window expired")
    if order.refunded_at is not None:
        raise HTTPException(status_code=409, detail="order already refunded")

    refund = Refund(order_id=order.id, amount=order.total)
    order.refunded_at = datetime.utcnow()
    db.add(refund)
    db.commit()
    db.refresh(refund)

    return RefundOut(
        id=refund.id,
        order_id=refund.order_id,
        amount=refund.amount,
        created_at=refund.created_at.isoformat(),
    )
