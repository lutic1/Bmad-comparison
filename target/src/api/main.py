from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.deps import engine
from api.models import Base
from api.routes import discount_codes, orders, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="benchmark-target", lifespan=lifespan)

app.include_router(users.router)
app.include_router(orders.router)
app.include_router(discount_codes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
