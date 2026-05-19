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


def _make_order(client, user, sku="A", quantity=1, unit_price=9.99):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": sku, "quantity": quantity, "unit_price": unit_price}]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_refund_requires_auth(client):
    user = _make_user(client, email="refund-auth@example.com")
    order = _make_order(client, user)
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_not_found(client):
    user = _make_user(client, email="refund-404@example.com")
    resp = client.post(
        "/orders/9999/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="refund-owner@example.com")
    other = _make_user(client, email="refund-other@example.com")
    order = _make_order(client, owner)
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )
    assert resp.status_code == 403


def test_refund_outside_30_day_window(client, monkeypatch):
    from datetime import timedelta

    user = _make_user(client, email="refund-expired@example.com")
    headers = {"X-User-Id": str(user["id"])}
    order = _make_order(client, user)

    from api.routes import orders as orders_module

    real_datetime = orders_module.datetime

    class FakeDatetime(real_datetime):
        @classmethod
        def utcnow(cls):
            return real_datetime.utcnow() + timedelta(days=31)

    monkeypatch.setattr(orders_module, "datetime", FakeDatetime)
    resp = client.post(f"/orders/{order['id']}/refund", headers=headers)
    assert resp.status_code == 400


def test_refund_success(client):
    user = _make_user(client, email="refund-ok@example.com")
    headers = {"X-User-Id": str(user["id"])}
    order = _make_order(client, user, sku="WIDGET", quantity=2, unit_price=9.99)

    resp = client.post(f"/orders/{order['id']}/refund", headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["amount"] == order["total"]
    assert body["amount"] == 1998
    assert "id" in body
    assert isinstance(body["created_at"], str)


def test_refund_already_refunded(client):
    user = _make_user(client, email="refund-twice@example.com")
    headers = {"X-User-Id": str(user["id"])}
    order = _make_order(client, user)

    first = client.post(f"/orders/{order['id']}/refund", headers=headers)
    assert first.status_code == 201
    second = client.post(f"/orders/{order['id']}/refund", headers=headers)
    assert second.status_code == 400
