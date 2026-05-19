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


# --- Refund endpoint tests ---

def _make_order(client, user_id, sku="SKU1", quantity=1, unit_price=10.00):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": quantity, "unit_price": unit_price}]},
    )
    assert resp.status_code == 201
    return resp.json()


def _set_created_at(db, order_id, delta):
    from datetime import datetime, timedelta
    from api.models import Order as OrderModel
    order = db.get(OrderModel, order_id)
    order.created_at = datetime.utcnow() - delta
    db.commit()


def test_refund_success(client):
    user = _make_user(client, email="refund_ok@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["total_refunded"] == order["total"]
    assert "refunded_at" in body and body["refunded_at"]


def test_refund_requires_auth(client):
    user = _make_user(client, email="refund_noauth@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_unknown_user(client):
    user = _make_user(client, email="refund_baduser@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": "99999"},
    )
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="refund_404@example.com")
    resp = client.post(
        "/orders/99999/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 404


def test_refund_forbidden_other_user(client):
    owner = _make_user(client, email="refund_owner@example.com")
    other = _make_user(client, email="refund_other@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )
    assert resp.status_code == 403


def test_refund_already_refunded(client):
    user = _make_user(client, email="refund_double@example.com")
    order = _make_order(client, user["id"])
    client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 409


def test_refund_expired_window(client, db):
    from datetime import timedelta
    user = _make_user(client, email="refund_expired@example.com")
    order = _make_order(client, user["id"])
    _set_created_at(db, order["id"], timedelta(days=31))
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 422


def test_refund_boundary_exactly_30_days(client, db):
    from datetime import timedelta
    user = _make_user(client, email="refund_boundary@example.com")
    order = _make_order(client, user["id"])
    # Set created_at to 1 second under 30 days ago — window uses >, so this is eligible.
    _set_created_at(db, order["id"], timedelta(days=30) - timedelta(seconds=1))
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 201


def test_refund_persists_state(client):
    user = _make_user(client, email="refund_persist@example.com")
    order = _make_order(client, user["id"])
    client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    resp = client.get(
        f"/orders/{order['id']}",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["refunded"] is True
    assert body["refunded_at"] is not None
