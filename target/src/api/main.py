from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.deps import SessionLocal, engine
from api.models import Base, DiscountCode
from api.routes import orders, users


def _seed_discount_codes() -> None:
    db = SessionLocal()
    try:
        for code, pct in [("SAVE5", 5), ("SAVE10", 10), ("SAVE20", 20)]:
            if db.query(DiscountCode).filter(DiscountCode.code == code).one_or_none() is None:
                db.add(DiscountCode(code=code, percentage=pct))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_discount_codes()
    yield


app = FastAPI(title="benchmark-target", lifespan=lifespan)

app.include_router(users.router)
app.include_router(orders.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
