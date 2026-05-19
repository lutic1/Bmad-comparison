from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.rate_limiter import RateLimiterMiddleware


def make_app(limit: int = 2, window_seconds: int = 60) -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    app.add_middleware(RateLimiterMiddleware, limit=limit, window_seconds=window_seconds)
    return app


@pytest.fixture
def rl_client():
    return TestClient(make_app(limit=2, window_seconds=60))


# --- US1: Enforcement ---


def test_request_over_limit_returns_429(rl_client):
    rl_client.get("/ping", headers={"X-User-Id": "u1"})
    rl_client.get("/ping", headers={"X-User-Id": "u1"})
    r = rl_client.get("/ping", headers={"X-User-Id": "u1"})
    assert r.status_code == 429
    body = r.json()
    assert body["detail"] == "Rate limit exceeded"
    assert isinstance(body["retry_after"], int)
    assert body["retry_after"] > 0


def test_429_includes_retry_after_header_and_zero_remaining(rl_client):
    rl_client.get("/ping", headers={"X-User-Id": "u2"})
    rl_client.get("/ping", headers={"X-User-Id": "u2"})
    r = rl_client.get("/ping", headers={"X-User-Id": "u2"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) > 0
    assert r.headers["X-RateLimit-Remaining"] == "0"


def test_scope_allowed_after_window_reset():
    base_time = 1_000_000.0
    app = make_app(limit=1, window_seconds=60)
    client = TestClient(app)

    with patch("api.middleware.rate_limiter.time") as mock_time:
        mock_time.time.return_value = base_time
        client.get("/ping", headers={"X-User-Id": "u3"})
        r = client.get("/ping", headers={"X-User-Id": "u3"})
        assert r.status_code == 429

        mock_time.time.return_value = base_time + 61
        r2 = client.get("/ping", headers={"X-User-Id": "u3"})
        assert r2.status_code == 200


# --- US2: Rate Limit Headers on All Responses ---


def test_200_response_includes_ratelimit_headers(rl_client):
    r = rl_client.get("/ping", headers={"X-User-Id": "u10"})
    assert r.status_code == 200
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers
    assert "X-RateLimit-Reset" in r.headers
    assert int(r.headers["X-RateLimit-Limit"]) == 2
    assert int(r.headers["X-RateLimit-Remaining"]) == 1
    assert int(r.headers["X-RateLimit-Reset"]) > 0


def test_remaining_decrements_per_request():
    client = TestClient(make_app(limit=5, window_seconds=60))
    r1 = client.get("/ping", headers={"X-User-Id": "u20"})
    r2 = client.get("/ping", headers={"X-User-Id": "u20"})
    r3 = client.get("/ping", headers={"X-User-Id": "u20"})
    assert r1.headers["X-RateLimit-Remaining"] == "4"
    assert r2.headers["X-RateLimit-Remaining"] == "3"
    assert r3.headers["X-RateLimit-Remaining"] == "2"


def test_independent_scopes_have_independent_counters():
    client = TestClient(make_app(limit=5, window_seconds=60))
    client.get("/ping", headers={"X-User-Id": "user_a"})
    client.get("/ping", headers={"X-User-Id": "user_a"})
    r_a = client.get("/ping", headers={"X-User-Id": "user_a"})
    r_b = client.get("/ping", headers={"X-User-Id": "user_b"})
    assert r_a.headers["X-RateLimit-Remaining"] == "2"
    assert r_b.headers["X-RateLimit-Remaining"] == "4"


def test_ip_fallback_scope_when_no_user_header():
    client = TestClient(make_app(limit=5, window_seconds=60))
    r1 = client.get("/ping")
    r2 = client.get("/ping")
    assert "X-RateLimit-Remaining" in r1.headers
    assert int(r1.headers["X-RateLimit-Remaining"]) == 4
    assert int(r2.headers["X-RateLimit-Remaining"]) == 3
