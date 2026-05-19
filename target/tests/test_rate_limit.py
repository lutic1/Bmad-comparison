import pytest

import api.rate_limit as rl


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    original_max = rl.MAX_REQUESTS
    original_window = rl.WINDOW_SECONDS
    rl._store.clear()
    rl.MAX_REQUESTS = 3
    yield
    rl._store.clear()
    rl.MAX_REQUESTS = original_max
    rl.WINDOW_SECONDS = original_window


def test_requests_within_limit_pass(client):
    for _ in range(rl.MAX_REQUESTS):
        resp = client.get("/users/1")
        assert resp.status_code != 429


def test_request_over_limit_returns_429(client):
    for _ in range(rl.MAX_REQUESTS):
        client.get("/users/1")
    resp = client.get("/users/1")
    assert resp.status_code == 429


def test_429_has_retry_after_header(client):
    for _ in range(rl.MAX_REQUESTS + 1):
        resp = client.get("/users/1")
    assert resp.status_code == 429
    assert "retry-after" in resp.headers
    assert int(resp.headers["retry-after"]) >= 1


def test_429_body_has_detail_field(client):
    for _ in range(rl.MAX_REQUESTS + 1):
        resp = client.get("/users/1")
    assert resp.status_code == 429
    body = resp.json()
    assert "detail" in body
    assert "Retry after" in body["detail"]


def test_health_endpoint_exempt(client):
    for _ in range(rl.MAX_REQUESTS * 10):
        resp = client.get("/health")
        assert resp.status_code == 200


def test_window_reset_allows_new_requests(client):
    for _ in range(rl.MAX_REQUESTS):
        client.get("/users/1")
    for key in list(rl._store):
        count, start = rl._store[key]
        rl._store[key] = (count, start - rl.WINDOW_SECONDS - 1)
    resp = client.get("/users/1")
    assert resp.status_code != 429


def test_different_identities_tracked_separately(client):
    for _ in range(rl.MAX_REQUESTS):
        client.get("/users/1", headers={"X-User-Id": "1"})
    resp = client.get("/users/1", headers={"X-User-Id": "2"})
    assert resp.status_code != 429


def test_env_var_override(client):
    rl.MAX_REQUESTS = 2
    for _ in range(2):
        client.get("/users/1")
    resp = client.get("/users/1")
    assert resp.status_code == 429
