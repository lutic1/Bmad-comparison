from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from api.models import Order, OrderItem, Refund, User


def _make_user(db_engine, email: str = "alice@example.com", name: str = "Alice") -> int:
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as db:
        user = User(email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def _make_order(
    db_engine,
    user_id: int,
    *,
    total_cents: int = 1998,
    created_at: datetime | None = None,
) -> int:
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as db:
        order = Order(user_id=user_id, total=total_cents)
        if created_at is not None:
            order.created_at = created_at
        db.add(order)
        db.flush()
        db.add(
            OrderItem(
                order_id=order.id, sku="abc", quantity=2, unit_price=999
            )
        )
        db.commit()
        db.refresh(order)
        return order.id


def _count_refunds(db_engine, order_id: int) -> int:
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as db:
        return (
            db.query(Refund).filter(Refund.order_id == order_id).count()
        )


def _get_order_refunded_at(db_engine, order_id: int) -> datetime | None:
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as db:
        return db.get(Order, order_id).refunded_at


def test_refund_recent_order_succeeds(client, db_engine):
    user_id = _make_user(db_engine)
    order_id = _make_order(
        db_engine,
        user_id,
        total_cents=1998,
        created_at=datetime.utcnow() - timedelta(days=5),
    )

    resp = client.post(
        f"/orders/{order_id}/refund", headers={"X-User-Id": str(user_id)}
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["order_id"] == order_id
    assert body["amount"] == 1998
    assert isinstance(body["id"], int) and body["id"] >= 1
    assert "created_at" in body and body["created_at"]

    assert _count_refunds(db_engine, order_id) == 1
    assert _get_order_refunded_at(db_engine, order_id) is not None


def test_refund_at_29_days_succeeds(client, db_engine):
    user_id = _make_user(db_engine)
    order_id = _make_order(
        db_engine,
        user_id,
        created_at=datetime.utcnow() - timedelta(days=29),
    )

    resp = client.post(
        f"/orders/{order_id}/refund", headers={"X-User-Id": str(user_id)}
    )

    assert resp.status_code == 201, resp.text


def test_refund_after_window_rejected(client, db_engine):
    user_id = _make_user(db_engine)
    order_id = _make_order(
        db_engine,
        user_id,
        created_at=datetime.utcnow() - timedelta(days=31),
    )

    resp = client.post(
        f"/orders/{order_id}/refund", headers={"X-User-Id": str(user_id)}
    )

    assert resp.status_code == 422
    assert resp.json()["detail"] == "refund window expired"
    assert _count_refunds(db_engine, order_id) == 0
    assert _get_order_refunded_at(db_engine, order_id) is None


def test_refund_unauthenticated_rejected(client, db_engine):
    user_id = _make_user(db_engine)
    order_id = _make_order(db_engine, user_id)

    resp = client.post(f"/orders/{order_id}/refund")

    assert resp.status_code == 401
    assert _count_refunds(db_engine, order_id) == 0


def test_refund_not_owner_returns_404(client, db_engine):
    owner_id = _make_user(db_engine, email="owner@example.com", name="Owner")
    other_id = _make_user(db_engine, email="other@example.com", name="Other")
    order_id = _make_order(db_engine, owner_id)

    resp = client.post(
        f"/orders/{order_id}/refund", headers={"X-User-Id": str(other_id)}
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "order not found"
    assert _count_refunds(db_engine, order_id) == 0


def test_refund_nonexistent_order_returns_404(client, db_engine):
    user_id = _make_user(db_engine)

    resp = client.post(
        "/orders/9999/refund", headers={"X-User-Id": str(user_id)}
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "order not found"


def test_refund_already_refunded_returns_409(client, db_engine):
    user_id = _make_user(db_engine)
    order_id = _make_order(db_engine, user_id)

    first = client.post(
        f"/orders/{order_id}/refund", headers={"X-User-Id": str(user_id)}
    )
    assert first.status_code == 201

    second = client.post(
        f"/orders/{order_id}/refund", headers={"X-User-Id": str(user_id)}
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "order already refunded"
    assert _count_refunds(db_engine, order_id) == 1
