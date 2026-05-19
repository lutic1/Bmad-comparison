from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from api.deps import engine
from api.models import Base
from api.rate_limit import check_rate_limit
from api.routes import orders, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="benchmark-target", lifespan=lifespan)

app.include_router(users.router, dependencies=[Depends(check_rate_limit)])
app.include_router(orders.router, dependencies=[Depends(check_rate_limit)])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
