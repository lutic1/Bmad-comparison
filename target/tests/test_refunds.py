from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from api.models import Order


def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_order(client, user_id, items=None):
    if items is None:
        items = [{"sku": "A", "quantity": 1, "unit_price": 9.99}]
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": items},
    )
    assert resp.status_code == 201
    return resp.json()


def _backdate_order(db_engine, order_id, days):
    with Session(db_engine) as session:
        order = session.get(Order, order_id)
        order.created_at = datetime.utcnow() - timedelta(days=days)
        session.commit()


def _read_order(db_engine, order_id):
    with Session(db_engine) as session:
        return session.get(Order, order_id)


def test_refund_eligible_order_returns_201_and_marks_order_refunded(client, db_engine):
    user = _make_user(client, email="ok@example.com")
    order = _make_order(client, user["id"])

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert set(body.keys()) == {"id", "order_id", "amount", "created_at"}
    assert body["order_id"] == order["id"]
    assert body["amount"] == order["total"]
    assert isinstance(body["id"], int)
    assert isinstance(body["created_at"], str)

    refreshed = _read_order(db_engine, order["id"])
    assert refreshed.refunded_at is not None


def test_refund_missing_x_user_id_returns_401(client):
    resp = client.post("/orders/1/refund")
    assert resp.status_code == 401
    assert "missing X-User-Id header" in resp.json()["detail"]


def test_refund_unknown_order_returns_404(client):
    user = _make_user(client, email="unknown@example.com")
    resp = client.post(
        "/orders/9999/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "order not found"


def test_refund_non_owner_returns_404(client):
    owner = _make_user(client, email="owner@example.com")
    other = _make_user(client, email="other@example.com")
    order = _make_order(client, owner["id"])

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "order not found"


def test_refund_order_older_than_30_days_returns_400(client, db_engine):
    user = _make_user(client, email="old@example.com")
    order = _make_order(client, user["id"])
    _backdate_order(db_engine, order["id"], days=31)

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )

    assert resp.status_code == 400
    assert "refund window expired" in resp.json()["detail"]


def test_refund_already_refunded_order_returns_409(client):
    user = _make_user(client, email="dup@example.com")
    order = _make_order(client, user["id"])

    first = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert first.status_code == 201

    second = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "order already refunded"
