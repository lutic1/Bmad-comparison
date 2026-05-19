from datetime import datetime, timedelta


def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_order(client, user_id, sku="WIDGET", qty=1, price=10.00):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": qty, "unit_price": price}]},
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# US1 — Successful Refund Request
# ---------------------------------------------------------------------------

def test_refund_success(client):
    user = _make_user(client, email="refund1@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["total"] == order["total"]
    assert "refunded_at" in body
    assert body["refunded_at"] is not None


def test_refund_already_refunded(client):
    user = _make_user(client, email="refund2@example.com")
    order = _make_order(client, user["id"])
    first = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert first.status_code == 200
    second = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "order already refunded"


# ---------------------------------------------------------------------------
# US2 — Ownership & Auth Violations
# ---------------------------------------------------------------------------

def test_refund_requires_auth(client):
    resp = client.post("/orders/1/refund")
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="refund3@example.com")
    resp = client.post(
        "/orders/99999/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 404


def test_refund_wrong_user(client):
    owner = _make_user(client, email="owner@refund.com")
    other = _make_user(client, email="other@refund.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# US3 — Expired Window
# ---------------------------------------------------------------------------

def test_refund_expired_window(client, db_engine):
    from sqlalchemy.orm import sessionmaker
    from api.models import Order

    user = _make_user(client, email="refund4@example.com")
    order = _make_order(client, user["id"])

    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        row = db.get(Order, order["id"])
        row.created_at = datetime.utcnow() - timedelta(days=31)
        db.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "refund window expired"


def test_refund_boundary_inclusive(client, db_engine):
    from sqlalchemy.orm import sessionmaker
    from api.models import Order

    user = _make_user(client, email="refund5@example.com")
    order = _make_order(client, user["id"])

    # 1 second inside the 30-day window to avoid microsecond race with utcnow()
    Session = sessionmaker(bind=db_engine)
    with Session() as db:
        row = db.get(Order, order["id"])
        row.created_at = datetime.utcnow() - timedelta(days=30) + timedelta(seconds=1)
        db.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 200
