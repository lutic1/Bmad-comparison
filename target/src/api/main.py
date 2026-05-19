from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from api.deps import engine
from api.models import Base
from api.rate_limit import rate_limit
from api.routes import orders, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="benchmark-target", lifespan=lifespan, dependencies=[Depends(rate_limit)])

app.include_router(users.router)
app.include_router(orders.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
