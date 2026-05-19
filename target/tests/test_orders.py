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


# ── Refund endpoint tests ──────────────────────────────────────────────────


def _make_order(client, user_id, sku="X", qty=1, price=1.00):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": qty, "unit_price": price}]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_refund_requires_auth(client):
    user = _make_user(client, email="auth1@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_unknown_user_401(client):
    user = _make_user(client, email="auth2@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": "99999"},
    )
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="notfound@example.com")
    resp = client.post(
        "/orders/9999/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="rfowner@example.com")
    other = _make_user(client, email="rfother@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )
    assert resp.status_code == 403


def test_refund_expired_window_422(client, db_session):
    from datetime import datetime, timedelta

    from api.models import Order

    owner = _make_user(client, email="expired@example.com")
    order = _make_order(client, owner["id"])

    row = db_session.get(Order, order["id"])
    row.created_at = datetime.utcnow() - timedelta(days=31)
    db_session.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 422
    assert "30 days" in resp.json()["detail"]


def test_refund_success_200(client):
    owner = _make_user(client, email="success@example.com")
    order = _make_order(client, owner["id"], price=9.99)

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["refunded"] is True
    assert body["refunded_at"] is not None
    assert body["total"] == 999


def test_refund_already_refunded_409(client):
    owner = _make_user(client, email="double@example.com")
    order = _make_order(client, owner["id"])

    client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 409


def test_refund_reflected_in_get_order(client):
    owner = _make_user(client, email="reflect@example.com")
    order = _make_order(client, owner["id"])

    client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    resp = client.get(
        f"/orders/{order['id']}",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["refunded"] is True
    assert body["refunded_at"] is not None
