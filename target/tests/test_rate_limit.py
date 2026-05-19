from api import rate_limit
from api.rate_limit import SlidingWindowLimiter


def test_requests_succeed_under_the_limit(client, monkeypatch):
    monkeypatch.setattr(rate_limit.limiter, "max_requests", 3)
    rate_limit.limiter.reset()

    for _ in range(3):
        r = client.get("/users/1")
        assert r.status_code in (200, 404)


def test_returns_429_when_limit_exceeded(client, monkeypatch):
    monkeypatch.setattr(rate_limit.limiter, "max_requests", 3)
    rate_limit.limiter.reset()

    for _ in range(3):
        client.get("/users/1")

    r = client.get("/users/1")
    assert r.status_code == 429
    assert r.json() == {"detail": "rate limit exceeded"}
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) >= 1


def test_health_endpoint_is_exempt(client, monkeypatch):
    monkeypatch.setattr(rate_limit.limiter, "max_requests", 2)
    rate_limit.limiter.reset()

    for _ in range(10):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_different_keys_have_independent_budgets():
    limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60.0)

    assert limiter.check("a") == (True, 0.0)
    assert limiter.check("a") == (True, 0.0)
    allowed_a, _ = limiter.check("a")
    assert allowed_a is False

    assert limiter.check("b") == (True, 0.0)
    assert limiter.check("b") == (True, 0.0)
    allowed_b, _ = limiter.check("b")
    assert allowed_b is False
