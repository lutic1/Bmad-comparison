def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
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
    _make_user(client)
    resp = client.post("/orders/1/refund")
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="missing@example.com")
    resp = client.post(
        "/orders/999/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="rowner@example.com")
    other = _make_user(client, email="rother@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()
    resp = client.post(
        f"/orders/{created['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )
    assert resp.status_code == 403


def test_refund_success(client):
    owner = _make_user(client, email="rok@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 2, "unit_price": 5.00}]},
    ).json()
    resp = client.post(
        f"/orders/{created['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == created["id"]
    assert body["amount"] == 1000
    assert body["refunded_at"]


def test_refund_second_call_rejected(client):
    owner = _make_user(client, email="ridem@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()
    headers = {"X-User-Id": str(owner["id"])}
    first = client.post(f"/orders/{created['id']}/refund", headers=headers)
    assert first.status_code == 200
    second = client.post(f"/orders/{created['id']}/refund", headers=headers)
    assert second.status_code == 400
    assert "already refunded" in second.json()["detail"]


def test_refund_window_expired(client, db_engine):
    from datetime import datetime, timedelta
    from sqlalchemy.orm import sessionmaker
    from api.models import Order

    owner = _make_user(client, email="rold@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()

    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as s:
        order = s.get(Order, created["id"])
        order.created_at = datetime.utcnow() - timedelta(days=31)
        s.commit()

    resp = client.post(
        f"/orders/{created['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 400
    assert "window" in resp.json()["detail"]
