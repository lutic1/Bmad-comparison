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
        json={"items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_refund_requires_auth(client):
    user = _make_user(client, email="auth@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="notfound@example.com")
    resp = client.post("/orders/999/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="owner@refund.com")
    other = _make_user(client, email="other@refund.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(other["id"])}
    )
    assert resp.status_code == 403


def test_refund_success(client):
    user = _make_user(client, email="success@refund.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert "id" in body
    assert "refunded_at" in body


def test_refund_already_refunded(client):
    user = _make_user(client, email="double@refund.com")
    order = _make_order(client, user["id"])
    client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 409


def test_refund_window_expired(client, db_engine):
    user = _make_user(client, email="expired@refund.com")
    order = _make_order(client, user["id"])

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        row = db.get(Order, order["id"])
        row.created_at = datetime.utcnow() - timedelta(days=31)
        db.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 422
