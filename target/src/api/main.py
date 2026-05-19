from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.deps import SessionLocal, engine
from api.models import Base, DiscountCode
from api.routes import orders, users
from api.routes import discounts


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for code_str, pct in [("SAVE5", 5), ("SAVE10", 10), ("SAVE20", 20)]:
            if not db.query(DiscountCode).filter_by(code=code_str).first():
                db.add(DiscountCode(code=code_str, discount_percent=pct))
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title="benchmark-target", lifespan=lifespan)

app.include_router(users.router)
app.include_router(orders.router)
app.include_router(discounts.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
