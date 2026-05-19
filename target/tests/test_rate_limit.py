import pytest

from api import rate_limit


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    rate_limit.reset()
    yield
    rate_limit.reset()


def _make_user(client, email):
    resp = client.post("/users", json={"email": email, "name": "x"})
    assert resp.status_code == 201
    return resp.json()


def test_under_limit_does_not_429(client):
    for _ in range(rate_limit.DEFAULT_LIMIT):
        resp = client.get("/users/99999")
        assert resp.status_code != 429
    assert resp.status_code == 404


def test_over_limit_public_returns_429(client):
    for _ in range(rate_limit.DEFAULT_LIMIT):
        client.get("/users/99999")
    resp = client.get("/users/99999")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_per_user_keying_on_orders(client):
    a = _make_user(client, email="a@example.com")
    b = _make_user(client, email="b@example.com")
    payload = {"items": [{"sku": "S", "quantity": 1, "unit_price": 1.0}]}
    for _ in range(rate_limit.DEFAULT_LIMIT):
        resp = client.post(
            "/orders", headers={"X-User-Id": str(a["id"])}, json=payload
        )
        assert resp.status_code != 429
    over = client.post(
        "/orders", headers={"X-User-Id": str(a["id"])}, json=payload
    )
    assert over.status_code == 429
    b_resp = client.post(
        "/orders", headers={"X-User-Id": str(b["id"])}, json=payload
    )
    assert b_resp.status_code == 201


def test_window_resets(client, monkeypatch):
    start = rate_limit._now()
    for _ in range(rate_limit.DEFAULT_LIMIT):
        client.get("/users/99999")
    over = client.get("/users/99999")
    assert over.status_code == 429
    monkeypatch.setattr(
        rate_limit, "_now", lambda: start + rate_limit.DEFAULT_WINDOW + 1
    )
    after = client.get("/users/99999")
    assert after.status_code != 429


def test_health_is_exempt(client):
    for _ in range(rate_limit.DEFAULT_LIMIT * 3):
        resp = client.get("/health")
        assert resp.status_code == 200
