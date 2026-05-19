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


# --- US1: Apply Valid Discount Code ---

def test_discount_10pct_reduces_total(client):
    user = _make_user(client, email="disc10@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}],
            "discount_code": "SAVE10",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1798  # 1998 - 10% = 1798.2 -> round -> 1798
    assert body["discount_code"] == "SAVE10"


def test_discount_5pct_reduces_total(client):
    user = _make_user(client, email="disc5@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}],
            "discount_code": "SAVE5",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1898  # 1998 - 5% = 1898.1 -> round -> 1898
    assert body["discount_code"] == "SAVE5"


def test_discount_20pct_reduces_total(client):
    user = _make_user(client, email="disc20@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}],
            "discount_code": "SAVE20",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1598  # 1998 - 20% = 1598.4 -> round -> 1598
    assert body["discount_code"] == "SAVE20"


# --- US2: Reject Invalid Discount Code ---

def test_invalid_discount_code_returns_422(client):
    user = _make_user(client, email="badisc@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "WIDGET", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "BOGUS",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Invalid discount code"


def test_blank_discount_code_treated_as_none(client):
    user = _make_user(client, email="blank@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "WIDGET", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "   ",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1000
    assert body["discount_code"] is None


# --- US3: Checkout Without Discount Code ---

def test_checkout_without_discount_code_unchanged(client):
    user = _make_user(client, email="nodiscount@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1998
    assert body["discount_code"] is None
