from datetime import datetime, timedelta

from sqlalchemy.orm import Session as DbSession

from api.models import Order as OrderModel


def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def test_create_order_requires_auth(client):
    _make_user(client)
    resp = client.post(
        "/orders",
        json={"items": [{"sku": "A", "quantity": 1, "unit_price": 9.99}]},
    )
    assert resp.status_code == 401


def test_create_order_stores_cents(client):
    user = _make_user(client, email="cents@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1998
    assert body["items"][0]["unit_price"] == 999


def test_create_order_empty_items_rejected(client):
    user = _make_user(client, email="empty@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": []},
    )
    assert resp.status_code == 400


def test_get_order_forbidden_for_other_user(client):
    owner = _make_user(client, email="owner@example.com")
    other = _make_user(client, email="other@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()
    resp = client.get(
        f"/orders/{created['id']}", headers={"X-User-Id": str(other["id"])}
    )
    assert resp.status_code == 403


def test_get_order_returns_owner(client):
    owner = _make_user(client, email="owner2@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()
    resp = client.get(
        f"/orders/{created['id']}", headers={"X-User-Id": str(owner["id"])}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


# ---------------------------------------------------------------------------
# Refund endpoint tests
# ---------------------------------------------------------------------------

def _make_order(client, user_id: int) -> dict:
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": "SKU-1", "quantity": 1, "unit_price": 10.00}]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_refund_success(client):
    user = _make_user(client, email="refund_ok@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["user_id"] == user["id"]
    assert "refunded_at" in body


def test_refund_at_30_day_boundary(client, db_engine):
    user = _make_user(client, email="boundary@example.com")
    order = _make_order(client, user["id"])
    with DbSession(db_engine) as db:
        o = db.get(OrderModel, order["id"])
        # 5 seconds inside the 30-day window to avoid sub-second timing drift
        o.created_at = datetime.utcnow() - timedelta(days=30) + timedelta(seconds=5)
        db.commit()
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 200


def test_refund_requires_auth(client):
    user = _make_user(client, email="noauth@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="notfound@example.com")
    resp = client.post(
        "/orders/99999/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Order not found"


def test_refund_wrong_owner(client):
    owner = _make_user(client, email="owner_ref@example.com")
    other = _make_user(client, email="other_ref@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Order not found"


def test_refund_window_expired(client, db_engine):
    user = _make_user(client, email="expired@example.com")
    order = _make_order(client, user["id"])
    with DbSession(db_engine) as db:
        o = db.get(OrderModel, order["id"])
        o.created_at = datetime.utcnow() - timedelta(days=30, seconds=1)
        db.commit()
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Refund window expired"


def test_refund_already_refunded(client):
    user = _make_user(client, email="dupe@example.com")
    order = _make_order(client, user["id"])
    client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Order already refunded"
