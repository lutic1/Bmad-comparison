from datetime import datetime, timedelta

from sqlalchemy import select

from api.models import Order, Refund


def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_order(client, user_id, sku="WIDGET", quantity=2, unit_price=9.99):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": quantity, "unit_price": unit_price}]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_refund_happy_path(client, db_engine):
    user = _make_user(client, email="refund-ok@example.com")
    order = _make_order(client, user["id"])

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

    from sqlalchemy.orm import Session

    with Session(bind=db_engine) as session:
        stored = session.get(Order, order["id"])
        assert stored is not None
        assert stored.refunded_at is not None
        refunds = session.execute(
            select(Refund).where(Refund.order_id == order["id"])
        ).scalars().all()
        assert len(refunds) == 1
        assert refunds[0].amount == order["total"]


def test_refund_requires_auth(client):
    resp = client.post("/orders/1/refund")
    assert resp.status_code == 401


def test_refund_not_found_for_missing_order(client):
    user = _make_user(client, email="missing@example.com")
    resp = client.post(
        "/orders/9999/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 404


def test_refund_not_found_when_owned_by_other_user(client, db_engine):
    owner = _make_user(client, email="owner@example.com")
    other = _make_user(client, email="other@example.com")
    order = _make_order(client, owner["id"])

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )

    assert resp.status_code == 404

    from sqlalchemy.orm import Session

    with Session(bind=db_engine) as session:
        stored = session.get(Order, order["id"])
        assert stored.refunded_at is None
        refunds = session.execute(
            select(Refund).where(Refund.order_id == order["id"])
        ).scalars().all()
        assert refunds == []


def test_refund_rejected_outside_30_day_window(client, db_engine):
    user = _make_user(client, email="old@example.com")
    order = _make_order(client, user["id"])

    from sqlalchemy.orm import Session

    with Session(bind=db_engine) as session:
        stored = session.get(Order, order["id"])
        stored.created_at = datetime.utcnow() - timedelta(days=31)
        session.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )

    assert resp.status_code == 400

    with Session(bind=db_engine) as session:
        stored = session.get(Order, order["id"])
        assert stored.refunded_at is None
        refunds = session.execute(
            select(Refund).where(Refund.order_id == order["id"])
        ).scalars().all()
        assert refunds == []


def test_refund_rejected_when_already_refunded(client, db_engine):
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

    from sqlalchemy.orm import Session

    with Session(bind=db_engine) as session:
        refunds = session.execute(
            select(Refund).where(Refund.order_id == order["id"])
        ).scalars().all()
        assert len(refunds) == 1
