import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import deps
from api.main import app
from api.models import Base
from api.rate_limit import RateLimiter, get_rate_limiter


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _make_client(db_engine, limiter: RateLimiter) -> TestClient:
    TestingSessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    return TestClient(app)


@pytest.fixture
def client(db_engine):
    with _make_client(db_engine, RateLimiter()) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def rate_limited_client(db_engine):
    with _make_client(db_engine, RateLimiter(limit=3, window_seconds=60)) as c:
        yield c
    app.dependency_overrides.clear()
