from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from api.models import Order, Refund


def _create_user(client, email: str = "a@example.com", name: str = "A") -> int:
    response = client.post("/users", json={"email": email, "name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_order(client, user_id: int) -> int:
    response = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": "sku-1", "quantity": 1, "unit_price": 9.99}]},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _set_order_created_at(db_engine, order_id: int, created_at: datetime) -> None:
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as s:
        order = s.get(Order, order_id)
        assert order is not None
        order.created_at = created_at
        s.commit()


def _count_refunds(db_engine) -> int:
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as s:
        return s.query(Refund).count()


def _get_order_refunded_at(db_engine, order_id: int):
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as s:
        order = s.get(Order, order_id)
        assert order is not None
        return order.refunded_at


# ---------- US1: happy path ----------


def test_refund_recent_order_succeeds(client, db_engine):
    user_id = _create_user(client)
    order_id = _create_order(client, user_id)

    response = client.post(
        f"/orders/{order_id}/refund",
        headers={"X-User-Id": str(user_id)},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["order_id"] == order_id
    assert isinstance(body["id"], int)
    assert isinstance(body["created_at"], str) and len(body["created_at"]) > 0
    assert _get_order_refunded_at(db_engine, order_id) is not None


def test_refund_on_30th_day_boundary_succeeds(client, db_engine):
    user_id = _create_user(client)
    order_id = _create_order(client, user_id)
    _set_order_created_at(
        db_engine, order_id, datetime.utcnow() - timedelta(days=30, hours=-1)
    )

    response = client.post(
        f"/orders/{order_id}/refund",
        headers={"X-User-Id": str(user_id)},
    )

    assert response.status_code == 201, response.text


# ---------- US2: ineligible orders ----------


def test_refund_unknown_order_returns_404(client, db_engine):
    user_id = _create_user(client)

    response = client.post(
        "/orders/99999/refund",
        headers={"X-User-Id": str(user_id)},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "order not found"
    assert _count_refunds(db_engine) == 0


def test_refund_not_owner_returns_403(client, db_engine):
    user_a = _create_user(client, email="a@example.com", name="A")
    user_b = _create_user(client, email="b@example.com", name="B")
    order_id = _create_order(client, user_a)

    response = client.post(
        f"/orders/{order_id}/refund",
        headers={"X-User-Id": str(user_b)},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "forbidden"
    assert _get_order_refunded_at(db_engine, order_id) is None
    assert _count_refunds(db_engine) == 0


def test_refund_outside_window_returns_400(client, db_engine):
    user_id = _create_user(client)
    order_id = _create_order(client, user_id)
    _set_order_created_at(
        db_engine, order_id, datetime.utcnow() - timedelta(days=31)
    )

    response = client.post(
        f"/orders/{order_id}/refund",
        headers={"X-User-Id": str(user_id)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "refund window expired"
    assert _get_order_refunded_at(db_engine, order_id) is None
    assert _count_refunds(db_engine) == 0


def test_refund_twice_returns_409(client, db_engine):
    user_id = _create_user(client)
    order_id = _create_order(client, user_id)

    first = client.post(
        f"/orders/{order_id}/refund",
        headers={"X-User-Id": str(user_id)},
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/orders/{order_id}/refund",
        headers={"X-User-Id": str(user_id)},
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "order already refunded"
    assert _count_refunds(db_engine) == 1


# ---------- US3: unauthenticated ----------


def test_refund_without_auth_header_returns_401(client, db_engine):
    user_id = _create_user(client)
    order_id = _create_order(client, user_id)

    response = client.post(f"/orders/{order_id}/refund")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing X-User-Id header"
    assert _get_order_refunded_at(db_engine, order_id) is None
    assert _count_refunds(db_engine) == 0


def test_refund_with_unknown_user_returns_401(client, db_engine):
    user_id = _create_user(client)
    order_id = _create_order(client, user_id)

    response = client.post(
        f"/orders/{order_id}/refund",
        headers={"X-User-Id": "99999"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "unknown user"
    assert _get_order_refunded_at(db_engine, order_id) is None
    assert _count_refunds(db_engine) == 0
