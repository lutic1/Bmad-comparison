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
    user = _make_user(client, email="nf@example.com")
    resp = client.post("/orders/99999/refund", headers={"X-User-Id": str(user["id"])})
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
    user = _make_user(client, email="refund@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["amount"] == order["total"]
    assert body["refunded_at"] is not None


def test_refund_already_refunded(client):
    user = _make_user(client, email="double@example.com")
    order = _make_order(client, user["id"])
    client.post(f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])})
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 409


def test_refund_outside_30_day_window(client, db_engine):
    user = _make_user(client, email="old@example.com")
    order = _make_order(client, user["id"])

    Session = sessionmaker(bind=db_engine)
    db = Session()
    db_order = db.get(Order, order["id"])
    db_order.created_at = datetime.utcnow() - timedelta(days=31)
    db.commit()
    db.close()

    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 422
