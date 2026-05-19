from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker as _sm

from api.models import Order


@pytest.fixture
def db(db_engine):
    session = _sm(bind=db_engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()


def _make_user(client, email="u@example.com", name="U"):
    r = client.post("/users", json={"email": email, "name": name})
    assert r.status_code == 201
    return r.json()


def _make_order(client, user_id, sku="SKU1", qty=1, price=10.00):
    r = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": qty, "unit_price": price}]},
    )
    assert r.status_code == 201
    return r.json()


def _backdate(db, order_id, days):
    order = db.get(Order, order_id)
    order.created_at = datetime.utcnow() - timedelta(days=days)
    db.commit()


def test_refund_requires_auth(client):
    user = _make_user(client, email="a1@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_unknown_user(client):
    user = _make_user(client, email="a2@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": "99999"})
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="a3@example.com")
    resp = client.post("/orders/99999/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "order not found"


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="a4owner@example.com")
    other = _make_user(client, email="a4other@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(other["id"])})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "forbidden"


def test_refund_already_refunded_returns_409(client):
    user = _make_user(client, email="a5@example.com")
    order = _make_order(client, user["id"])
    client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    resp = client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "order already refunded"


def test_refund_expired_window_rejected(client, db):
    user = _make_user(client, email="a6@example.com")
    order = _make_order(client, user["id"])
    _backdate(db, order["id"], days=31)
    resp = client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "refund window expired"


def test_refund_within_window_succeeds(client):
    user = _make_user(client, email="a7@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 201


def test_refund_at_boundary_succeeds(client, db):
    user = _make_user(client, email="a8@example.com")
    order = _make_order(client, user["id"])
    # Set to 30 days minus 1 minute — clearly inside window, tests boundary region
    order_obj = db.get(Order, order["id"])
    order_obj.created_at = datetime.utcnow() - timedelta(days=30) + timedelta(minutes=1)
    db.commit()
    resp = client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 201


def test_refund_sets_refunded_flag_and_timestamp(client):
    user = _make_user(client, email="a9@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 201
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["refunded_at"] is not None


def test_refund_visible_on_get_order(client):
    user = _make_user(client, email="a10@example.com")
    order = _make_order(client, user["id"])
    client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    resp = client.get(f"/orders/{order['id']}", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 200
    body = resp.json()
    assert body["refunded"] is True
    assert body["refunded_at"] is not None


def test_refund_returns_201(client):
    user = _make_user(client, email="a11@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 201


def test_refund_response_shape(client):
    user = _make_user(client, email="a12@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 201
    body = resp.json()
    assert isinstance(body["order_id"], int)
    assert isinstance(body["refunded_at"], str)
    assert isinstance(body["total"], int)
    assert body["order_id"] == order["id"]
    assert body["total"] == order["total"]
