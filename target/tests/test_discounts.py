import pytest
from api.models import DiscountCode


def _make_user(client, email="u@example.com", name="U"):
    resp = client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


def _make_order(client, user_id, unit_price=10.0, quantity=1, sku="ITEM"):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": quantity, "unit_price": unit_price}]},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture(autouse=True)
def discount_codes(db_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    db = Session()
    for code, pct in [("SAVE5", 5), ("SAVE10", 10), ("SAVE20", 20)]:
        db.add(DiscountCode(code=code, discount_percent=pct))
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# US1: Apply valid discount code
# ---------------------------------------------------------------------------

def test_apply_save5_reduces_total_by_5_percent(client):
    user = _make_user(client, email="a@example.com")
    order = _make_order(client, user["id"], unit_price=10.0)  # 1000 cents
    resp = client.post(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE5"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 950
    assert body["discount_amount_cents"] == 50
    assert body["discount_code"] == "SAVE5"


def test_apply_save10_reduces_total_by_10_percent(client):
    user = _make_user(client, email="b@example.com")
    order = _make_order(client, user["id"], unit_price=10.0)  # 1000 cents
    resp = client.post(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE10"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 900
    assert body["discount_amount_cents"] == 100
    assert body["discount_code"] == "SAVE10"


def test_apply_save20_reduces_total_by_20_percent(client):
    user = _make_user(client, email="c@example.com")
    order = _make_order(client, user["id"], unit_price=10.0)  # 1000 cents
    resp = client.post(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE20"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 800
    assert body["discount_amount_cents"] == 200
    assert body["discount_code"] == "SAVE20"


def test_apply_second_code_replaces_first_and_recalculates(client):
    user = _make_user(client, email="d@example.com")
    order = _make_order(client, user["id"], unit_price=10.0)  # 1000 cents
    client.post(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE10"},
    )
    resp = client.post(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE20"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 800
    assert body["discount_amount_cents"] == 200
    assert body["discount_code"] == "SAVE20"


# ---------------------------------------------------------------------------
# US2: Reject invalid discount code
# ---------------------------------------------------------------------------

def test_apply_unrecognized_code_returns_422(client):
    user = _make_user(client, email="e@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "FAKE99"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "invalid discount code"


def test_apply_without_auth_header_returns_401(client):
    user = _make_user(client, email="f@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/discount-code",
        json={"code": "SAVE10"},
    )
    assert resp.status_code == 401


def test_apply_to_other_users_order_returns_403(client):
    owner = _make_user(client, email="g@example.com")
    other = _make_user(client, email="h@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(other["id"])},
        json={"code": "SAVE10"},
    )
    assert resp.status_code == 403


def test_apply_to_nonexistent_order_returns_404(client):
    user = _make_user(client, email="i@example.com")
    resp = client.post(
        "/orders/99999/discount-code",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE10"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# US3: Remove applied discount code
# ---------------------------------------------------------------------------

def test_remove_applied_code_restores_original_total(client):
    user = _make_user(client, email="j@example.com")
    order = _make_order(client, user["id"], unit_price=10.0)  # 1000 cents
    client.post(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "SAVE10"},
    )
    resp = client.delete(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1000
    assert body["discount_code"] is None
    assert body["discount_amount_cents"] == 0


def test_remove_when_no_code_applied_returns_400(client):
    user = _make_user(client, email="k@example.com")
    order = _make_order(client, user["id"])
    resp = client.delete(
        f"/orders/{order['id']}/discount-code",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "no discount code applied"
