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


def test_create_order_applies_valid_discount(client):
    user = _make_user(client, email="disc@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}],
            "discount_code": "SAVE10",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["total"] == 1799


def test_create_order_rejects_invalid_discount(client):
    user = _make_user(client, email="bogus@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}],
            "discount_code": "BOGUS",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid discount code"


def test_create_order_without_discount_unchanged(client):
    user = _make_user(client, email="nodisc@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}]},
    )
    assert resp.status_code == 201
    assert resp.json()["total"] == 1998


def test_create_order_discount_code_case_insensitive(client):
    user = _make_user(client, email="case@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}],
            "discount_code": "save20",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["total"] == 1599


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
