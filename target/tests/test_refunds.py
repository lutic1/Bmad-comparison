from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from api.models import Order, Refund


def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_order(client, user_id, unit_price=10.00):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": "A", "quantity": 1, "unit_price": unit_price}]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_refund_happy_path_returns_refund_record(client):
    user = _make_user(client, email="happy@example.com")
    order = _make_order(client, user["id"], unit_price=12.50)

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["amount"] == order["total"]
    assert isinstance(body["id"], int)
    assert isinstance(body["created_at"], str) and body["created_at"]


def test_refund_returns_404_when_order_missing(client):
    user = _make_user(client, email="missing@example.com")

    resp = client.post(
        "/orders/999999/refund",
        headers={"X-User-Id": str(user["id"])},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "order not found"


def test_refund_returns_403_when_not_owner(client):
    owner = _make_user(client, email="owner@example.com")
    other = _make_user(client, email="other@example.com")
    order = _make_order(client, owner["id"])

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "forbidden"


def test_refund_returns_400_when_outside_30_day_window(client, db_engine):
    user = _make_user(client, email="old@example.com")
    order = _make_order(client, user["id"])

    session_factory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        db_order = session.get(Order, order["id"])
        db_order.created_at = datetime.utcnow() - timedelta(days=31)
        session.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "refund window expired"

    with session_factory() as session:
        db_order = session.get(Order, order["id"])
        assert db_order.refunded_at is None
        assert (
            session.query(Refund).filter_by(order_id=order["id"]).count() == 0
        )


def test_refund_returns_409_when_already_refunded(client, db_engine):
    user = _make_user(client, email="twice@example.com")
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

    session_factory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        assert (
            session.query(Refund).filter_by(order_id=order["id"]).count() == 1
        )


def test_refund_returns_401_when_unauthenticated(client):
    user = _make_user(client, email="anon@example.com")
    order = _make_order(client, user["id"])

    resp = client.post(f"/orders/{order['id']}/refund")

    assert resp.status_code == 401

    follow_up = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert follow_up.status_code == 201
