from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_db
from api.models import DiscountCode

router = APIRouter(prefix="/discount-codes", tags=["discount-codes"])


class DiscountCodeCreate(BaseModel):
    code: str
    pct: Literal[5, 10, 20]


class DiscountCodeRead(BaseModel):
    id: int
    code: str
    pct: int

    class Config:
        from_attributes = True


@router.post("", response_model=DiscountCodeRead, status_code=201)
def create_discount_code(payload: DiscountCodeCreate, db: Session = Depends(get_db)) -> DiscountCode:
    existing = db.query(DiscountCode).filter(DiscountCode.code == payload.code).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="discount code already exists")
    dc = DiscountCode(code=payload.code, pct=payload.pct)
    db.add(dc)
    db.commit()
    db.refresh(dc)
    return dc
