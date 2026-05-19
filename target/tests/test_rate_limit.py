from api.main import app
from api.rate_limit import get_rate_limiter


def _create_user(client, email: str = "rl@example.com", name: str = "RL User") -> int:
    r = client.post("/users", json={"email": email, "name": name})
    return r.json()["id"]


# --- US1: Excess Requests Rejected ---


def test_request_within_quota_is_allowed(rate_limited_client):
    user_id = _create_user(rate_limited_client)
    r = rate_limited_client.get(f"/users/{user_id}", headers={"X-User-Id": str(user_id)})
    assert r.status_code == 200


def test_request_exceeding_quota_returns_429(rate_limited_client):
    user_id = _create_user(rate_limited_client)
    headers = {"X-User-Id": str(user_id)}
    for _ in range(3):
        rate_limited_client.get(f"/users/{user_id}", headers=headers)
    r = rate_limited_client.get(f"/users/{user_id}", headers=headers)
    assert r.status_code == 429


def test_429_body_detail(rate_limited_client):
    user_id = _create_user(rate_limited_client)
    headers = {"X-User-Id": str(user_id)}
    for _ in range(3):
        rate_limited_client.get(f"/users/{user_id}", headers=headers)
    r = rate_limited_client.get(f"/users/{user_id}", headers=headers)
    assert r.json() == {"detail": "rate limit exceeded"}


def test_client_counters_are_independent(rate_limited_client):
    user_a = _create_user(rate_limited_client, email="a@example.com", name="A")
    user_b = _create_user(rate_limited_client, email="b@example.com", name="B")
    for _ in range(3):
        rate_limited_client.get(f"/users/{user_a}", headers={"X-User-Id": str(user_a)})
    r = rate_limited_client.get(f"/users/{user_b}", headers={"X-User-Id": str(user_b)})
    assert r.status_code == 200


def test_unauthenticated_request_returns_401_not_429(rate_limited_client):
    r = rate_limited_client.post("/orders", json={})
    assert r.status_code == 401


# --- US2: Rate Limit Transparency via Headers ---


def test_rate_limit_headers_present_on_200(client):
    user_id = _create_user(client)
    r = client.get(f"/users/{user_id}", headers={"X-User-Id": str(user_id)})
    assert r.status_code == 200
    assert r.headers["X-RateLimit-Limit"] == "100"
    assert int(r.headers["X-RateLimit-Remaining"]) == 99
    assert int(r.headers["X-RateLimit-Reset"]) > 0


def test_remaining_decrements_per_request(client):
    user_id = _create_user(client)
    headers = {"X-User-Id": str(user_id)}
    r1 = client.get(f"/users/{user_id}", headers=headers)
    r2 = client.get(f"/users/{user_id}", headers=headers)
    r3 = client.get(f"/users/{user_id}", headers=headers)
    assert int(r1.headers["X-RateLimit-Remaining"]) == 99
    assert int(r2.headers["X-RateLimit-Remaining"]) == 98
    assert int(r3.headers["X-RateLimit-Remaining"]) == 97


def test_429_includes_retry_after_and_zero_remaining(rate_limited_client):
    user_id = _create_user(rate_limited_client)
    headers = {"X-User-Id": str(user_id)}
    for _ in range(3):
        rate_limited_client.get(f"/users/{user_id}", headers=headers)
    r = rate_limited_client.get(f"/users/{user_id}", headers=headers)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    assert r.headers["X-RateLimit-Remaining"] == "0"


def test_window_reset_clears_counter(rate_limited_client):
    user_id = _create_user(rate_limited_client)
    headers = {"X-User-Id": str(user_id)}
    for _ in range(3):
        rate_limited_client.get(f"/users/{user_id}", headers=headers)
    r = rate_limited_client.get(f"/users/{user_id}", headers=headers)
    assert r.status_code == 429

    limiter = app.dependency_overrides[get_rate_limiter]()
    count, window_start = limiter._counts[user_id]
    limiter._counts[user_id] = (count, window_start - limiter.window_seconds - 1)

    r = rate_limited_client.get(f"/users/{user_id}", headers=headers)
    assert r.status_code == 200
    assert int(r.headers["X-RateLimit-Remaining"]) == limiter.limit - 1
