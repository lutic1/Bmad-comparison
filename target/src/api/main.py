from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from api.deps import engine
from api.models import Base, DiscountCode
from api.routes import orders, users

_SEED_CODES = [("SAVE5", 5), ("SAVE10", 10), ("SAVE20", 20)]


def seed_discount_codes(db: Session) -> None:
    for code, pct in _SEED_CODES:
        if not db.query(DiscountCode).filter_by(code=code).first():
            db.add(DiscountCode(code=code, percentage=pct))
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    from sqlalchemy.orm import sessionmaker
    db = sessionmaker(bind=engine)()
    try:
        seed_discount_codes(db)
    finally:
        db.close()
    yield


app = FastAPI(title="benchmark-target", lifespan=lifespan)

app.include_router(users.router)
app.include_router(orders.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
