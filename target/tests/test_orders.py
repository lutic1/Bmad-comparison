from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from api.models import Order


def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_order(client, user_id, sku="X", quantity=1, unit_price=10.00):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": quantity, "unit_price": unit_price}]},
    )
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


def test_refund_requires_auth(client):
    owner = _make_user(client, email="refund-auth@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    owner = _make_user(client, email="refund-404@example.com")
    resp = client.post(
        "/orders/9999/refund", headers={"X-User-Id": str(owner["id"])}
    )
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="refund-owner@example.com")
    other = _make_user(client, email="refund-other@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )
    assert resp.status_code == 403


def test_refund_happy_path(client, db_engine):
    owner = _make_user(client, email="refund-ok@example.com")
    order = _make_order(client, owner["id"], unit_price=12.50, quantity=2)
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["amount"] == 2500
    assert body["refunded_at"]

    Session = sessionmaker(bind=db_engine)
    with Session() as s:
        persisted = s.get(Order, order["id"])
        assert persisted.refunded_at is not None


def test_refund_outside_window_rejected(client, db_engine):
    owner = _make_user(client, email="refund-old@example.com")
    order = _make_order(client, owner["id"])

    Session = sessionmaker(bind=db_engine)
    with Session() as s:
        persisted = s.get(Order, order["id"])
        persisted.created_at = datetime.utcnow() - timedelta(days=31)
        s.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "refund window expired"


def test_refund_already_refunded(client):
    owner = _make_user(client, email="refund-twice@example.com")
    order = _make_order(client, owner["id"])
    first = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert first.status_code == 201

    second = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert second.status_code == 400
    assert second.json()["detail"] == "order already refunded"
