import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import api.middleware.rate_limit as rl_module
from api import deps
from api.main import app


@pytest.fixture
def rate_limit_client(db_engine):
    store = rl_module._store
    original_limit = store._limit
    original_window = store._window
    store._limit = 2
    store._window = 1
    store._store.clear()

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
    with TestClient(app) as c:
        yield c

    store._limit = original_limit
    store._window = original_window
    store._store.clear()
    app.dependency_overrides.clear()


# US1: Throttling Enforcement

def test_request_within_limit_succeeds(rate_limit_client):
    assert rate_limit_client.get("/health").status_code == 200
    assert rate_limit_client.get("/health").status_code == 200


def test_request_exceeding_limit_returns_429(rate_limit_client):
    rate_limit_client.get("/health")
    rate_limit_client.get("/health")
    r = rate_limit_client.get("/health")
    assert r.status_code == 429
    assert r.json() == {"detail": "Rate limit exceeded"}


def test_window_reset_allows_requests_again(rate_limit_client):
    rate_limit_client.get("/health")
    rate_limit_client.get("/health")
    assert rate_limit_client.get("/health").status_code == 429
    time.sleep(1.1)
    assert rate_limit_client.get("/health").status_code == 200


# US2: Rate Limit Status Visibility

def test_rate_limit_headers_present_on_success(rate_limit_client):
    r = rate_limit_client.get("/health")
    assert r.status_code == 200
    assert "x-ratelimit-limit" in r.headers
    assert "x-ratelimit-remaining" in r.headers
    assert "x-ratelimit-reset" in r.headers


def test_remaining_decrements_per_request(rate_limit_client):
    r1 = rate_limit_client.get("/health")
    r2 = rate_limit_client.get("/health")
    assert int(r1.headers["x-ratelimit-remaining"]) > int(r2.headers["x-ratelimit-remaining"])


def test_429_includes_retry_after(rate_limit_client):
    rate_limit_client.get("/health")
    rate_limit_client.get("/health")
    r = rate_limit_client.get("/health")
    assert r.status_code == 429
    assert "retry-after" in r.headers
    assert int(r.headers["retry-after"]) >= 1


# US3: Per-Client Isolation

def test_throttled_user_does_not_affect_other_user(rate_limit_client):
    for _ in range(3):
        rate_limit_client.get("/health", headers={"X-User-Id": "1"})
    r = rate_limit_client.get("/health", headers={"X-User-Id": "2"})
    assert r.status_code == 200


def test_authenticated_and_unauthenticated_clients_are_isolated(rate_limit_client):
    for _ in range(3):
        rate_limit_client.get("/health")  # unauthenticated — keyed by IP
    r = rate_limit_client.get("/health", headers={"X-User-Id": "42"})
    assert r.status_code == 200
