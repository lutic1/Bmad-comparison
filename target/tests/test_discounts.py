from api.models import DiscountCode


def _make_user(client, email="buyer@example.com", name="Buyer"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _seed_code(
    db,
    code: str = "SAVE10",
    percentage: int = 10,
    is_active: bool = True,
    max_uses: int | None = None,
    times_used: int = 0,
) -> DiscountCode:
    dc = DiscountCode(
        code=code,
        percentage=percentage,
        is_active=is_active,
        max_uses=max_uses,
        times_used=times_used,
    )
    db.add(dc)
    db.commit()
    db.refresh(dc)
    return dc


_ITEMS = [{"sku": "X", "quantity": 1, "unit_price": 100.00}]  # 10000 cents


def test_discount_applied_correct_total(client, db):
    user = _make_user(client)
    _seed_code(db, code="SAVE10", percentage=10)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS, "discount_code": "SAVE10"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["original_total"] == 10000
    assert body["total"] == 9000
    assert body["discount_code"] == "SAVE10"
    assert body["discount_percentage"] == 10


def test_discount_times_used_incremented(client, db):
    user = _make_user(client, email="tui@example.com")
    dc = _seed_code(db, code="INC10", percentage=10)
    client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS, "discount_code": "INC10"},
    )
    db.refresh(dc)
    assert dc.times_used == 1


def test_discount_5pct_rounding(client, db):
    user = _make_user(client, email="round@example.com")
    _seed_code(db, code="SAVE5", percentage=5)
    # 1001 cents * 95 // 100 = 950 (floor, not 951)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "Y", "quantity": 1, "unit_price": 10.01}], "discount_code": "SAVE5"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["original_total"] == 1001
    assert body["total"] == 950


def test_discount_20pct(client, db):
    user = _make_user(client, email="twenty@example.com")
    _seed_code(db, code="SAVE20", percentage=20)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS, "discount_code": "SAVE20"},
    )
    assert resp.status_code == 201
    assert resp.json()["total"] == 8000


def test_no_discount_code_backward_compat(client):
    user = _make_user(client, email="nocode@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["discount_code"] is None
    assert body["discount_percentage"] is None
    assert body["original_total"] == body["total"]


def test_unknown_code_returns_400(client):
    user = _make_user(client, email="unk@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS, "discount_code": "FAKE"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "discount code not found"


def test_inactive_code_returns_400(client, db):
    user = _make_user(client, email="inactive@example.com")
    _seed_code(db, code="OFF10", percentage=10, is_active=False)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS, "discount_code": "OFF10"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "discount code is not active"


def test_exhausted_single_use_code_returns_400(client, db):
    user = _make_user(client, email="exhaust@example.com")
    _seed_code(db, code="ONCE", percentage=10, max_uses=1, times_used=1)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS, "discount_code": "ONCE"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "discount code has been fully redeemed"


def test_case_insensitive_lookup(client, db):
    user = _make_user(client, email="case@example.com")
    _seed_code(db, code="SAVE10", percentage=10)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS, "discount_code": "save10"},
    )
    assert resp.status_code == 201
    assert resp.json()["discount_code"] == "SAVE10"


def test_get_order_returns_discount_fields(client, db):
    user = _make_user(client, email="getdisc@example.com")
    _seed_code(db, code="SAVE10", percentage=10)
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS, "discount_code": "SAVE10"},
    ).json()
    resp = client.get(
        f"/orders/{created['id']}",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_code"] == "SAVE10"
    assert body["discount_percentage"] == 10
    assert body["original_total"] == 10000
    assert body["total"] == 9000


def test_get_order_no_discount_fields_null(client):
    user = _make_user(client, email="getnull@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": _ITEMS},
    ).json()
    resp = client.get(
        f"/orders/{created['id']}",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_code"] is None
    assert body["discount_percentage"] is None
    assert body["original_total"] == body["total"]
