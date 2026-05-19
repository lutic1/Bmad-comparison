import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.rate_limit import RateLimitMiddleware


def _make_app(limit: int, store: dict) -> FastAPI:
    test_app = FastAPI()

    @test_app.get("/ping")
    def ping():
        return {"ok": True}

    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    test_app.add_middleware(RateLimitMiddleware, limit=limit, store=store)
    return test_app


@pytest.fixture
def rate_limit_client():
    store: dict = {}
    app = _make_app(limit=3, store=store)
    with TestClient(app) as c:
        yield c, store


def test_requests_under_limit_succeed(rate_limit_client):
    client, _ = rate_limit_client
    for _ in range(3):
        assert client.get("/ping").status_code == 200


def test_request_exceeding_limit_returns_429(rate_limit_client):
    client, _ = rate_limit_client
    for _ in range(3):
        client.get("/ping")
    resp = client.get("/ping")
    assert resp.status_code == 429
    assert resp.json() == {"detail": "Rate limit exceeded"}


def test_429_body_is_json(rate_limit_client):
    client, _ = rate_limit_client
    for _ in range(4):
        client.get("/ping")
    resp = client.get("/ping")
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["detail"] == "Rate limit exceeded"


def test_health_endpoint_skipped(rate_limit_client):
    client, _ = rate_limit_client
    for _ in range(4):
        client.get("/ping")
    assert client.get("/health").status_code == 200


def test_window_reset_allows_requests_again():
    store: dict = {}
    app = _make_app(limit=2, store=store)
    with TestClient(app) as client:
        client.get("/ping")
        client.get("/ping")
        assert client.get("/ping").status_code == 429

        ip = list(store.keys())[0]
        count, window_start = store[ip]
        store[ip] = (count, window_start - 61.0)

        assert client.get("/ping").status_code == 200
