from datetime import timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from api.models import Order


@pytest.fixture
def db(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_order(client, user_id):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_refund_requires_auth(client):
    user = _make_user(client)
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client)
    resp = client.post("/orders/999/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="owner@example.com")
    other = _make_user(client, email="other@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(other["id"])}
    )
    assert resp.status_code == 403


def test_refund_success(client):
    user = _make_user(client, email="success@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert "id" in body
    assert "created_at" in body


def test_refund_already_refunded(client):
    user = _make_user(client, email="double@example.com")
    order = _make_order(client, user["id"])
    headers = {"X-User-Id": str(user["id"])}
    client.post(f"/orders/{order['id']}/refund", headers=headers)
    resp = client.post(f"/orders/{order['id']}/refund", headers=headers)
    assert resp.status_code == 409


def test_refund_outside_window(client, db):
    user = _make_user(client, email="old@example.com")
    order = _make_order(client, user["id"])

    row = db.get(Order, order["id"])
    row.created_at = row.created_at - timedelta(days=31)
    db.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 400
