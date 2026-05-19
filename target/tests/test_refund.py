from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from api.models import Order


def _make_user(client, email: str = "u@test.com", name: str = "U") -> int:
    r = client.post("/users", json={"email": email, "name": name})
    assert r.status_code == 201
    return r.json()["id"]


def _make_order(client, user_id: int) -> int:
    r = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": "SKU-1", "quantity": 1, "unit_price": 9.99}]},
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_refund_success(client):
    user_id = _make_user(client)
    order_id = _make_order(client, user_id)

    r = client.post(f"/orders/{order_id}/refund", headers={"X-User-Id": str(user_id)})

    assert r.status_code == 200
    body = r.json()
    assert body["order_id"] == order_id
    assert body["amount"] == 999
    assert "refunded_at" in body


def test_refund_no_auth(client):
    user_id = _make_user(client, email="noauth@test.com")
    order_id = _make_order(client, user_id)

    r = client.post(f"/orders/{order_id}/refund")

    assert r.status_code == 401


def test_refund_order_not_found(client):
    user_id = _make_user(client, email="notfound@test.com")

    r = client.post("/orders/99999/refund", headers={"X-User-Id": str(user_id)})

    assert r.status_code == 404


def test_refund_wrong_user(client):
    owner_id = _make_user(client, email="owner@test.com", name="Owner")
    other_id = _make_user(client, email="other@test.com", name="Other")
    order_id = _make_order(client, owner_id)

    r = client.post(f"/orders/{order_id}/refund", headers={"X-User-Id": str(other_id)})

    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden"


def test_refund_window_expired(client, db_engine):
    user_id = _make_user(client, email="expired@test.com")
    order_id = _make_order(client, user_id)

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        order = session.get(Order, order_id)
        order.created_at = datetime.utcnow() - timedelta(days=31)
        session.commit()

    r = client.post(f"/orders/{order_id}/refund", headers={"X-User-Id": str(user_id)})

    assert r.status_code == 422
    assert r.json()["detail"] == "refund window expired"


def test_refund_already_refunded(client):
    user_id = _make_user(client, email="twice@test.com")
    order_id = _make_order(client, user_id)

    first = client.post(f"/orders/{order_id}/refund", headers={"X-User-Id": str(user_id)})
    assert first.status_code == 200

    second = client.post(f"/orders/{order_id}/refund", headers={"X-User-Id": str(user_id)})
    assert second.status_code == 422
    assert second.json()["detail"] == "order already refunded"
