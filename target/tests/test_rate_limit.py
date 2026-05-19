import pytest

from api import rate_limit


@pytest.fixture(autouse=True)
def reset_rate_limiter(monkeypatch):
    monkeypatch.setattr(rate_limit, "_LIMIT", 3)
    rate_limit._store.clear()
    yield
    rate_limit._store.clear()


def _make_user(client, email="rl@example.com", name="RL"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def test_requests_within_limit_succeed(client):
    for _ in range(3):
        resp = client.get("/health")
        # health is exempt; use users endpoint instead
    user = _make_user(client, email="a1@example.com")
    rate_limit._store.clear()
    for i in range(3):
        resp = client.get(f"/users/{user['id']}", headers={"X-User-Id": str(user["id"])})
        assert resp.status_code == 200


def test_request_over_limit_returns_429(client):
    user = _make_user(client, email="a2@example.com")
    rate_limit._store.clear()
    uid = str(user["id"])
    for _ in range(3):
        client.get(f"/users/{user['id']}", headers={"X-User-Id": uid})
    resp = client.get(f"/users/{user['id']}", headers={"X-User-Id": uid})
    assert resp.status_code == 429
    assert resp.json()["detail"] == "rate limit exceeded"


def test_429_includes_retry_after_header(client):
    user = _make_user(client, email="a3@example.com")
    rate_limit._store.clear()
    uid = str(user["id"])
    for _ in range(3):
        client.get(f"/users/{user['id']}", headers={"X-User-Id": uid})
    resp = client.get(f"/users/{user['id']}", headers={"X-User-Id": uid})
    assert resp.status_code == 429
    assert "retry-after" in resp.headers
    assert int(resp.headers["retry-after"]) >= 1


def test_different_users_have_independent_counters(client):
    u1 = _make_user(client, email="b1@example.com")
    u2 = _make_user(client, email="b2@example.com")
    rate_limit._store.clear()
    for _ in range(3):
        client.get(f"/users/{u1['id']}", headers={"X-User-Id": str(u1["id"])})
    # u1 is now at limit; u2 should still be fine
    resp = client.get(f"/users/{u2['id']}", headers={"X-User-Id": str(u2["id"])})
    assert resp.status_code == 200


def test_unauthenticated_request_is_rate_limited_by_ip(client):
    for i in range(3):
        client.post("/users", json={"email": f"ip{i}@example.com", "name": f"IP{i}"})
    resp = client.post("/users", json={"email": "ip_over@example.com", "name": "Over"})
    assert resp.status_code == 429


def test_health_endpoint_is_never_rate_limited(client):
    for _ in range(10):
        resp = client.get("/health")
        assert resp.status_code == 200
