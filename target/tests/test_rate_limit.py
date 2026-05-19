import time

from api.middleware.rate_limit import RATE_LIMIT_REQUESTS, _counters, _lock


def test_requests_below_limit_succeed(client):
    for _ in range(3):
        resp = client.get("/health")
        assert resp.status_code == 200


def test_request_above_limit_returns_429(client):
    with _lock:
        _counters["user:1"] = (999, time.monotonic())
    resp = client.get("/health", headers={"X-User-Id": "1"})
    assert resp.status_code == 429


def test_429_retry_after_header_is_integer(client):
    with _lock:
        _counters["user:2"] = (999, time.monotonic())
    resp = client.get("/health", headers={"X-User-Id": "2"})
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) > 0


def test_429_body_shape(client):
    with _lock:
        _counters["user:3"] = (999, time.monotonic())
    resp = client.get("/health", headers={"X-User-Id": "3"})
    assert resp.status_code == 429
    body = resp.json()
    assert "detail" in body
    assert "Rate limit exceeded" in body["detail"]


def test_route_handler_not_invoked_on_429(client, db_engine):
    from sqlalchemy.orm import sessionmaker
    from api.models import User

    with _lock:
        _counters["user:42"] = (999, time.monotonic())

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        before = session.query(User).count()

    resp = client.post(
        "/users",
        json={"email": "shouldnotexist@example.com", "name": "Ghost"},
        headers={"X-User-Id": "42"},
    )
    assert resp.status_code == 429

    with Session() as session:
        after = session.query(User).count()
    assert before == after


def test_different_users_have_independent_counters(client):
    with _lock:
        _counters["user:10"] = (999, time.monotonic())
    resp = client.get("/health", headers={"X-User-Id": "11"})
    assert resp.status_code == 200


def test_no_user_id_falls_back_to_ip(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_window_reset_clears_counter(client):
    expired_start = time.monotonic() - 9999
    with _lock:
        _counters["user:20"] = (999, expired_start)
    resp = client.get("/health", headers={"X-User-Id": "20"})
    assert resp.status_code == 200


def test_configurable_limit_threshold_is_enforced(client):
    with _lock:
        _counters["user:50"] = (RATE_LIMIT_REQUESTS, time.monotonic())
    resp = client.get("/health", headers={"X-User-Id": "50"})
    assert resp.status_code == 429


def test_ip_subject_key_is_rate_limited(client):
    with _lock:
        _counters["ip:testclient"] = (RATE_LIMIT_REQUESTS, time.monotonic())
    resp = client.get("/health")
    assert resp.status_code == 429
