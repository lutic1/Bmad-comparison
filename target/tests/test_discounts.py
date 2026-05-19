from sqlalchemy.orm import sessionmaker

from api.models import Order, OrderItem


def _make_user(client, email="d@example.com", name="D"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def test_no_code_unchanged_behaviour(client):
    """PRD AC-1 — without discount_code, total matches today's behaviour."""
    user = _make_user(client, email="nocode@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 1998
    assert body.get("discount_code") is None
    assert body.get("discount_percent") is None
    assert body.get("discount_cents") is None


def test_save5_applied(client):
    """PRD AC-2 — SAVE5 on a $10.00 subtotal yields 950 cents."""
    user = _make_user(client, email="s5@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "SAVE5",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 950
    assert body["discount_code"] == "SAVE5"
    assert body["discount_percent"] == 5
    assert body["discount_cents"] == 50


def test_save10_applied(client):
    """PRD AC-2 — SAVE10 on a $10.00 subtotal yields 900 cents."""
    user = _make_user(client, email="s10@example.com")
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
    assert body["discount_percent"] == 10
    assert body["discount_cents"] == 100


def test_save20_applied(client):
    """PRD AC-2 — SAVE20 on a $10.00 subtotal yields 800 cents."""
    user = _make_user(client, email="s20@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "SAVE20",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 800
    assert body["discount_code"] == "SAVE20"
    assert body["discount_percent"] == 20
    assert body["discount_cents"] == 200


def test_rounding_half_up_boundary(client):
    """PRD AC-3 — subtotal 999c × SAVE10 = 999*0.10 = 99.9 → half-up 100."""
    user = _make_user(client, email="round@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 9.99}],
            "discount_code": "SAVE10",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 899
    assert body["discount_cents"] == 100


def test_code_is_case_insensitive(client):
    """PRD AC-4 — lower- and mixed-case variants are accepted; stored canonical."""
    user = _make_user(client, email="case@example.com")
    for variant in ("save10", "Save10", "  SAVE10  "):
        resp = client.post(
            "/orders",
            headers={"X-User-Id": str(user["id"])},
            json={
                "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
                "discount_code": variant,
            },
        )
        assert resp.status_code == 201, variant
        body = resp.json()
        assert body["total"] == 900
        assert body["discount_code"] == "SAVE10"


def test_invalid_code_returns_400_and_writes_nothing(client, db_engine):
    """PRD AC-5 — unknown code → 400; no orders, no order_items written."""
    user = _make_user(client, email="bad@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "NOPE",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid discount code"

    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as s:
        assert s.query(Order).count() == 0
        assert s.query(OrderItem).count() == 0


def test_empty_string_code_returns_400(client, db_engine):
    """PRD AC-5 — empty-string code is invalid, no rows written."""
    user = _make_user(client, email="empty@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "",
        },
    )
    assert resp.status_code == 400

    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as s:
        assert s.query(Order).count() == 0


def test_get_order_returns_discount_fields(client):
    """PRD AC-6 — GET surfaces canonical code, percent, and cents."""
    user = _make_user(client, email="get@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "save20",
        },
    ).json()

    resp = client.get(
        f"/orders/{created['id']}", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_code"] == "SAVE20"
    assert body["discount_percent"] == 20
    assert body["discount_cents"] == 200
    assert body["total"] == 800


def test_get_order_without_discount_returns_null_fields(client):
    """PRD AC-6 — GET on an order created without a code returns null fields."""
    user = _make_user(client, email="getnull@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}]},
    ).json()

    resp = client.get(
        f"/orders/{created['id']}", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("discount_code") is None
    assert body.get("discount_percent") is None
    assert body.get("discount_cents") is None


def test_missing_x_user_id_still_401_with_discount(client):
    """PRD AC-7 — auth boundary unchanged: missing header → 401."""
    resp = client.post(
        "/orders",
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "SAVE10",
        },
    )
    assert resp.status_code == 401


def test_unknown_user_still_401_with_discount(client):
    """PRD AC-7 — auth boundary unchanged: unknown user → 401."""
    resp = client.post(
        "/orders",
        headers={"X-User-Id": "99999"},
        json={
            "items": [{"sku": "A", "quantity": 1, "unit_price": 10.00}],
            "discount_code": "SAVE10",
        },
    )
    assert resp.status_code == 401


def test_total_and_discount_cents_are_integers(client):
    """PRD AC-8 — stored values are non-negative integers."""
    user = _make_user(client, email="int@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [{"sku": "A", "quantity": 3, "unit_price": 7.77}],
            "discount_code": "SAVE5",
        },
    )
    body = resp.json()
    assert isinstance(body["total"], int)
    assert isinstance(body["discount_cents"], int)
    assert body["total"] >= 0
    assert body["discount_cents"] >= 0
