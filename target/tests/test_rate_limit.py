import pytest

from api.middleware.rate_limit import limiter


@pytest.fixture
def small_limit():
    original_max = limiter.max_requests
    original_window = limiter.window_seconds
    limiter.max_requests = 3
    limiter.window_seconds = 60
    limiter.reset()
    yield
    limiter.max_requests = original_max
    limiter.window_seconds = original_window
    limiter.reset()


def test_under_limit_allows_requests(client, small_limit):
    for i in range(3):
        resp = client.post(
            "/users", json={"email": f"u{i}@example.com", "name": f"U{i}"}
        )
        assert resp.status_code == 201


def test_over_limit_returns_429_with_retry_after(client, small_limit):
    for i in range(3):
        client.post(
            "/users", json={"email": f"a{i}@example.com", "name": f"A{i}"}
        )
    resp = client.post(
        "/users", json={"email": "blocked@example.com", "name": "Blocked"}
    )
    assert resp.status_code == 429
    assert resp.json() == {"detail": "rate limit exceeded"}
    retry_after = resp.headers.get("Retry-After")
    assert retry_after is not None
    assert int(retry_after) >= 1


def test_per_user_isolation(client, small_limit):
    create = client.post(
        "/users", json={"email": "owner1@example.com", "name": "O1"}
    ).json()
    other = client.post(
        "/users", json={"email": "owner2@example.com", "name": "O2"}
    ).json()
    limiter.reset()

    for _ in range(3):
        resp = client.get(f"/users/{create['id']}", headers={"X-User-Id": "1"})
        assert resp.status_code == 200

    blocked = client.get(f"/users/{create['id']}", headers={"X-User-Id": "1"})
    assert blocked.status_code == 429

    allowed = client.get(f"/users/{other['id']}", headers={"X-User-Id": "2"})
    assert allowed.status_code == 200


def test_health_endpoint_is_exempt(client, small_limit):
    for _ in range(20):
        resp = client.get("/health")
        assert resp.status_code == 200


def test_window_reset_after_limiter_reset(client, small_limit):
    for i in range(3):
        client.post(
            "/users", json={"email": f"w{i}@example.com", "name": f"W{i}"}
        )
    blocked = client.post(
        "/users", json={"email": "wb@example.com", "name": "WB"}
    )
    assert blocked.status_code == 429

    limiter.reset()

    resp = client.post(
        "/users", json={"email": "after@example.com", "name": "After"}
    )
    assert resp.status_code == 201
