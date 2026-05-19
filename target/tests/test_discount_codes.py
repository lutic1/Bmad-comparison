def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_discount_code(client, code="SAVE10", pct=10):
    resp = client.post("/discount-codes", json={"code": code, "pct": pct})
    assert resp.status_code == 201
    return resp.json()


def test_create_discount_code(client):
    resp = client.post("/discount-codes", json={"code": "SAVE10", "pct": 10})
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "SAVE10"
    assert body["pct"] == 10


def test_create_discount_code_duplicate_rejected(client):
    _make_discount_code(client)
    resp = client.post("/discount-codes", json={"code": "SAVE10", "pct": 10})
    assert resp.status_code == 409


def test_create_discount_code_invalid_pct_rejected(client):
    resp = client.post("/discount-codes", json={"code": "BAD", "pct": 15})
    assert resp.status_code == 422


def test_order_with_discount_code_applies_discount(client):
    user = _make_user(client)
    _make_discount_code(client, code="SAVE10", pct=10)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "SAVE10",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 900
    assert body["discount_code"] == "SAVE10"
    assert body["discount_pct"] == 10


def test_order_with_invalid_discount_code_returns_400(client):
    user = _make_user(client)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "NOTREAL",
        },
    )
    assert resp.status_code == 400


def test_order_without_discount_code_has_null_discount_fields(client):
    user = _make_user(client)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["discount_code"] is None
    assert body["discount_pct"] is None


def test_get_order_returns_discount_fields(client):
    user = _make_user(client)
    _make_discount_code(client, code="SAVE20", pct=20)
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "B", "quantity": 1, "unit_price": 5.00}],
            "discount_code": "SAVE20",
        },
    ).json()
    resp = client.get(f"/orders/{created['id']}", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_pct"] == 20
    assert body["discount_code"] == "SAVE20"


def test_order_5pct_discount_truncates_correctly(client):
    user = _make_user(client)
    _make_discount_code(client, code="SAVE5", pct=5)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "C", "quantity": 1, "unit_price": 9.99}],
            "discount_code": "SAVE5",
        },
    )
    assert resp.status_code == 201
    # 999 cents * 5% = 49.95 -> int() = 49 cents off -> total = 950
    assert resp.json()["total"] == 950


def test_order_20pct_discount(client):
    user = _make_user(client)
    _make_discount_code(client, code="SAVE20", pct=20)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "D", "quantity": 2, "unit_price": 10.00}],
            "discount_code": "SAVE20",
        },
    )
    assert resp.status_code == 201
    # 2000 cents - 20% = 1600 cents
    assert resp.json()["total"] == 1600
