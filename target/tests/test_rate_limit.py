import pytest

import api.rate_limit as rl


@pytest.fixture(autouse=True)
def patch_rate_limit(monkeypatch):
    monkeypatch.setattr(rl, "LIMIT", 2)
    rl._counters.clear()
    yield
    rl._counters.clear()


def test_requests_within_limit_succeed(client):
    resp1 = client.get("/health")
    resp2 = client.get("/health")
    assert resp1.status_code == 200
    assert resp2.status_code == 200


def test_request_exceeding_limit_returns_429(client):
    client.get("/health")
    client.get("/health")
    resp = client.get("/health")
    assert resp.status_code == 429
    assert resp.json()["detail"] == "rate limit exceeded"
    assert "retry-after" in resp.headers


def test_different_users_have_independent_limits(client):
    # Exhaust user 1's limit
    client.get("/health", headers={"X-User-Id": "1"})
    client.get("/health", headers={"X-User-Id": "1"})
    assert client.get("/health", headers={"X-User-Id": "1"}).status_code == 429

    # User 2 is unaffected
    assert client.get("/health", headers={"X-User-Id": "2"}).status_code == 200


def test_anonymous_requests_are_rate_limited(client):
    client.get("/health")
    client.get("/health")
    resp = client.get("/health")
    assert resp.status_code == 429
