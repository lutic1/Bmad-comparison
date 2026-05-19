from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api import deps
from api.main import app
from api.models import Base, Order


def _make_user(client: TestClient, email: str = "u@example.com") -> int:
    r = client.post("/users", json={"email": email, "name": "Test"})
    assert r.status_code == 201
    return r.json()["id"]


def _make_order(client: TestClient, user_id: int) -> int:
    r = client.post(
        "/orders",
        json={"items": [{"sku": "A1", "quantity": 1, "unit_price": 10.0}]},
        headers={"X-User-Id": str(user_id)},
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_refund_success(client):
    uid = _make_user(client)
    oid = _make_order(client, uid)

    r = client.post(f"/orders/{oid}/refund", headers={"X-User-Id": str(uid)})

    assert r.status_code == 201
    body = r.json()
    assert body["order_id"] == oid
    assert body["amount"] == 1000
    assert "id" in body
    assert "refunded_at" in body


def test_refund_missing_auth(client):
    uid = _make_user(client)
    oid = _make_order(client, uid)

    r = client.post(f"/orders/{oid}/refund")

    assert r.status_code == 401


def test_refund_order_not_found(client):
    uid = _make_user(client)

    r = client.post("/orders/9999/refund", headers={"X-User-Id": str(uid)})

    assert r.status_code == 404


def test_refund_wrong_user(client):
    uid1 = _make_user(client, "a@example.com")
    uid2 = _make_user(client, "b@example.com")
    oid = _make_order(client, uid1)

    r = client.post(f"/orders/{oid}/refund", headers={"X-User-Id": str(uid2)})

    assert r.status_code == 403


def test_refund_already_refunded(client):
    uid = _make_user(client)
    oid = _make_order(client, uid)

    client.post(f"/orders/{oid}/refund", headers={"X-User-Id": str(uid)})
    r = client.post(f"/orders/{oid}/refund", headers={"X-User-Id": str(uid)})

    assert r.status_code == 409


def test_refund_window_expired(client, db_engine):
    uid = _make_user(client)
    oid = _make_order(client, uid)

    with Session(db_engine) as db:
        order = db.get(Order, oid)
        order.created_at = datetime.utcnow() - timedelta(days=31)
        db.commit()

    r = client.post(f"/orders/{oid}/refund", headers={"X-User-Id": str(uid)})

    assert r.status_code == 422
