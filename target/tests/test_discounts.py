def _make_user(client, *, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_user_and_order(client, *, email, subtotal_cents):
    user = _make_user(client, email=email)
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={
            "items": [
                {"sku": "X", "quantity": 1, "unit_price": subtotal_cents / 100}
            ]
        },
    )
    assert resp.status_code == 201, resp.text
    order = resp.json()
    assert order["total"] == subtotal_cents
    return user, order


def test_apply_save5_discounts_by_5_percent(client):
    user, order = _make_user_and_order(
        client, email="us1a@example.com", subtotal_cents=10000
    )
    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE5"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["subtotal"] == 10000
    assert body["discount_code"] == "SAVE5"
    assert body["total"] == 9500


def test_apply_save10_discounts_by_10_percent(client):
    user, order = _make_user_and_order(
        client, email="us1b@example.com", subtotal_cents=10000
    )
    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE10"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 9000


def test_apply_save20_discounts_by_20_percent(client):
    user, order = _make_user_and_order(
        client, email="us1c@example.com", subtotal_cents=5000
    )
    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE20"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 4000


def test_apply_discount_is_case_insensitive(client):
    user, order = _make_user_and_order(
        client, email="us1d@example.com", subtotal_cents=10000
    )
    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "save10"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["discount_code"] == "SAVE10"
    assert body["total"] == 9000


def test_apply_discount_rounds_half_up(client):
    user, order = _make_user_and_order(
        client, email="us1e@example.com", subtotal_cents=999
    )
    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE10"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 899


def test_apply_discount_on_zero_subtotal_is_accepted(client):
    user = _make_user(client, email="us1f@example.com")
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "FREE", "quantity": 1, "unit_price": 0.00}]},
    )
    assert resp.status_code == 201
    order = resp.json()
    assert order["total"] == 0

    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE10"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["subtotal"] == 0
    assert body["discount_code"] == "SAVE10"


def test_apply_discount_forbidden_for_other_user(client):
    owner, order = _make_user_and_order(
        client, email="us1g_owner@example.com", subtotal_cents=10000
    )
    other = _make_user(client, email="us1g_other@example.com")
    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(other["id"])},
        json={"code": "SAVE10"},
    )
    assert resp.status_code == 403

    follow_up = client.get(
        f"/orders/{order['id']}", headers={"X-User-Id": str(owner["id"])}
    )
    assert follow_up.status_code == 200
    body = follow_up.json()
    assert body["total"] == 10000
    assert body["discount_code"] is None


def test_apply_discount_unknown_order_returns_404(client):
    user = _make_user(client, email="us1h@example.com")
    resp = client.post(
        "/orders/999/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE10"},
    )
    assert resp.status_code == 404


def test_apply_discount_requires_auth(client):
    _make_user(client, email="us1i@example.com")
    resp = client.post("/orders/1/discount", json={"code": "SAVE10"})
    assert resp.status_code == 401


def test_apply_unknown_code_returns_400_and_does_not_change_total(client):
    user, order = _make_user_and_order(
        client, email="us2a@example.com", subtotal_cents=10000
    )
    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "NOPE123"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid discount code"

    follow_up = client.get(
        f"/orders/{order['id']}", headers={"X-User-Id": str(user["id"])}
    )
    body = follow_up.json()
    assert body["total"] == 10000
    assert body["discount_code"] is None


def test_apply_empty_code_returns_400(client):
    user, order = _make_user_and_order(
        client, email="us2b@example.com", subtotal_cents=10000
    )
    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": ""},
    )
    assert resp.status_code == 400

    follow_up = client.get(
        f"/orders/{order['id']}", headers={"X-User-Id": str(user["id"])}
    )
    assert follow_up.json()["total"] == 10000


def test_apply_code_for_unsupported_percentage_returns_400(client):
    user, order = _make_user_and_order(
        client, email="us2c@example.com", subtotal_cents=10000
    )
    resp = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE15"},
    )
    assert resp.status_code == 400

    follow_up = client.get(
        f"/orders/{order['id']}", headers={"X-User-Id": str(user["id"])}
    )
    assert follow_up.json()["total"] == 10000


def test_apply_second_code_replaces_first(client):
    user, order = _make_user_and_order(
        client, email="us3a@example.com", subtotal_cents=10000
    )

    first = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE5"},
    )
    assert first.status_code == 200
    assert first.json()["total"] == 9500

    second = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE20"},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["total"] == 8000
    assert body["subtotal"] == 10000
    assert body["discount_code"] == "SAVE20"


def test_apply_then_invalid_code_keeps_first_discount(client):
    user, order = _make_user_and_order(
        client, email="us3b@example.com", subtotal_cents=10000
    )

    first = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE10"},
    )
    assert first.status_code == 200
    assert first.json()["total"] == 9000

    bad = client.post(
        f"/orders/{order['id']}/discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "NOPE"},
    )
    assert bad.status_code == 400

    follow_up = client.get(
        f"/orders/{order['id']}", headers={"X-User-Id": str(user["id"])}
    )
    body = follow_up.json()
    assert body["total"] == 9000
    assert body["subtotal"] == 10000
    assert body["discount_code"] == "SAVE10"
