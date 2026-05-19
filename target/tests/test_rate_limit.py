import time
from collections import deque

import pytest

from api.middleware import RATE_LIMIT, WINDOW_SECONDS, _buckets


@pytest.fixture
def rate_limit_client(client):
    _buckets.clear()
    yield client
    _buckets.clear()


def _fill_bucket(ip: str = "testclient", age: float = 0.0) -> None:
    now = time.time()
    _buckets[ip] = deque(now - age for _ in range(RATE_LIMIT))


def test_requests_below_limit_succeed(rate_limit_client):
    for _ in range(RATE_LIMIT - 1):
        assert rate_limit_client.get("/health").status_code == 200


def test_60th_request_succeeds(rate_limit_client):
    for _ in range(RATE_LIMIT):
        resp = rate_limit_client.get("/health")
    assert resp.status_code == 200


def test_61st_request_returns_429(rate_limit_client):
    _fill_bucket()
    assert rate_limit_client.get("/health").status_code == 429


def test_429_response_body(rate_limit_client):
    _fill_bucket()
    assert rate_limit_client.get("/health").text == "Too Many Requests"


def test_window_expiry_allows_new_requests(rate_limit_client):
    _fill_bucket(age=WINDOW_SECONDS + 1)
    assert rate_limit_client.get("/health").status_code == 200


def test_rate_limit_applies_to_all_routes(rate_limit_client):
    _fill_bucket()
    assert rate_limit_client.get("/users/1").status_code == 429


def test_different_ips_are_independent(rate_limit_client):
    _fill_bucket(ip="192.168.1.1")
    assert rate_limit_client.get("/health").status_code == 200
