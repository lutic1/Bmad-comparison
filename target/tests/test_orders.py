from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from api.models import Order


def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_order(client, user_id):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": "A", "quantity": 1, "unit_price": 5.00}]},
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
    user = _make_user(client, email="refauth@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="refnotfound@example.com")
    resp = client.post("/orders/99999/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="refowner@example.com")
    other = _make_user(client, email="refother@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(other["id"])}
    )
    assert resp.status_code == 403


def test_refund_succeeds_within_30_days(client):
    user = _make_user(client, email="refsuccess@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["user_id"] == user["id"]
    assert "refunded_at" in body


def test_refund_window_expired(client, db_engine):
    user = _make_user(client, email="refexpired@example.com")
    order = _make_order(client, user["id"])

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        db_order = db.get(Order, order["id"])
        db_order.created_at = datetime.utcnow() - timedelta(days=31)
        db.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "refund window expired"


def test_refund_already_refunded(client):
    user = _make_user(client, email="refdouble@example.com")
    order = _make_order(client, user["id"])
    headers = {"X-User-Id": str(user["id"])}
    client.post(f"/orders/{order['id']}/refund", headers=headers)
    resp = client.post(f"/orders/{order['id']}/refund", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "order already refunded"
