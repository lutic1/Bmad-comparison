from api.models import DiscountCode


def _make_user(client, email="u@example.com", name="U"):
    r = client.post("/users", json={"email": email, "name": name})
    assert r.status_code == 201
    return r.json()


def _seed_code(db, code: str, percentage: int):
    dc = DiscountCode(code=code, percentage=percentage)
    db.add(dc)
    db.commit()


def _create_order(client, user_id: int, unit_price: float = 10.00, quantity: int = 1, discount_code=None):
    body = {"items": [{"sku": "X", "quantity": quantity, "unit_price": unit_price}]}
    if discount_code is not None:
        body["discount_code"] = discount_code
    return client.post("/orders", headers={"X-User-Id": str(user_id)}, json=body)


def test_discount_5_percent(client, db):
    _seed_code(db, "SAVE5", 5)
    user = _make_user(client, email="d5@example.com")
    resp = _create_order(client, user["id"], unit_price=10.00, quantity=1, discount_code="SAVE5")
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1000
    assert body["discount_code"] == "SAVE5"
    assert body["discounted_total"] == round(1000 * 0.95)


def test_discount_10_percent(client, db):
    _seed_code(db, "SAVE10", 10)
    user = _make_user(client, email="d10@example.com")
    resp = _create_order(client, user["id"], unit_price=10.00, quantity=1, discount_code="SAVE10")
    assert resp.status_code == 201
    body = resp.json()
    assert body["discounted_total"] == round(1000 * 0.90)


def test_discount_20_percent(client, db):
    _seed_code(db, "SAVE20", 20)
    user = _make_user(client, email="d20@example.com")
    resp = _create_order(client, user["id"], unit_price=10.00, quantity=1, discount_code="SAVE20")
    assert resp.status_code == 201
    body = resp.json()
    assert body["discounted_total"] == round(1000 * 0.80)


def test_unknown_discount_code_returns_422(client, db):
    user = _make_user(client, email="unknown@example.com")
    resp = _create_order(client, user["id"], discount_code="NOPE")
    assert resp.status_code == 422
    assert "NOPE" in resp.json()["detail"]


def test_no_discount_code_regression(client):
    user = _make_user(client, email="nodiscount@example.com")
    resp = _create_order(client, user["id"], unit_price=9.99, quantity=2)
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1998


def test_no_discount_fields_are_null(client):
    user = _make_user(client, email="nullfields@example.com")
    resp = _create_order(client, user["id"])
    assert resp.status_code == 201
    body = resp.json()
    assert body["discount_code"] is None
    assert body["discounted_total"] is None


def test_discount_visible_on_get_order(client, db):
    _seed_code(db, "GET10", 10)
    user = _make_user(client, email="getorder@example.com")
    created = _create_order(client, user["id"], unit_price=10.00, discount_code="GET10").json()
    resp = client.get(f"/orders/{created['id']}", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_code"] == "GET10"
    assert body["discounted_total"] == created["discounted_total"]
