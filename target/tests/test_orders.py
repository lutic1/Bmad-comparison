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


_ITEMS_2x999 = [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}]  # 2×999¢ = 1998¢


def test_discount_no_code_regression(client):
    user = _make_user(client, email="nocode@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS_2x999},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1998
    assert body["discount_code"] is None
    assert body["discount_pct"] is None


def test_discount_5pct(client, discount_codes):
    user = _make_user(client, email="save5@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS_2x999, "discount_code": "SAVE5"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == round(1998 * 0.95)  # 1898
    assert body["discount_pct"] == 5
    assert body["discount_code"] == "SAVE5"


def test_discount_10pct(client, discount_codes):
    user = _make_user(client, email="save10@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS_2x999, "discount_code": "SAVE10"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == round(1998 * 0.90)  # 1798
    assert body["discount_pct"] == 10
    assert body["discount_code"] == "SAVE10"


def test_discount_20pct(client, discount_codes):
    user = _make_user(client, email="save20@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS_2x999, "discount_code": "SAVE20"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == round(1998 * 0.80)  # 1598
    assert body["discount_pct"] == 20
    assert body["discount_code"] == "SAVE20"


def test_discount_unknown_code(client, discount_codes, db):
    from api.models import Order
    user = _make_user(client, email="bogus@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS_2x999, "discount_code": "BOGUS"},
    )
    assert resp.status_code == 422
    assert "BOGUS" in resp.json()["detail"]
    assert db.query(Order).count() == 0


def test_discount_case_insensitive(client, discount_codes):
    user = _make_user(client, email="lower@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS_2x999, "discount_code": "save10"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["discount_pct"] == 10
    assert body["discount_code"] == "SAVE10"


def test_discount_fields_on_get_order(client, discount_codes):
    user = _make_user(client, email="getorder@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS_2x999, "discount_code": "SAVE10"},
    ).json()
    resp = client.get(
        f"/orders/{created['id']}", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_code"] == "SAVE10"
    assert body["discount_pct"] == 10
