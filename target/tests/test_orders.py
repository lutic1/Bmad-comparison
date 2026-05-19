import pytest
from sqlalchemy.orm import sessionmaker

from api.models import DiscountCode


@pytest.fixture
def make_discount_code(db_engine):
    def _make(code="SAVE10", percentage=10, is_active=True):
        Session = sessionmaker(bind=db_engine)
        db = Session()
        dc = DiscountCode(code=code.upper(), percentage=percentage, is_active=is_active)
        db.add(dc)
        db.commit()
        db.close()
        return code.upper()
    return _make


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


# ---------------------------------------------------------------------------
# Discount code tests
# ---------------------------------------------------------------------------

def _make_order(client, user_id: int, unit_price: float = 100.00) -> dict:
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": "WIDGET", "quantity": 1, "unit_price": unit_price}]},
    )
    assert resp.status_code == 201
    return resp.json()


# T004 — happy-path: all three discount tiers

def test_apply_discount_5_percent(client, make_discount_code):
    code = make_discount_code(code="FIVE", percentage=5)
    user = _make_user(client, email="five@example.com")
    order = _make_order(client, user["id"], unit_price=100.00)  # 10000 cents

    resp = client.post(
        f"/orders/{order['id']}/apply-discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": code},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["subtotal"] == 10000
    assert body["discount_percentage"] == 5
    assert body["discount_amount"] == 500
    assert body["final_total"] == 9500
    assert body["discount_code"] == "FIVE"


def test_apply_discount_10_percent(client, make_discount_code):
    code = make_discount_code(code="TEN", percentage=10)
    user = _make_user(client, email="ten@example.com")
    order = _make_order(client, user["id"], unit_price=100.00)  # 10000 cents

    resp = client.post(
        f"/orders/{order['id']}/apply-discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": code},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["subtotal"] == 10000
    assert body["discount_percentage"] == 10
    assert body["discount_amount"] == 1000
    assert body["final_total"] == 9000
    assert body["discount_code"] == "TEN"


def test_apply_discount_20_percent(client, make_discount_code):
    code = make_discount_code(code="TWENTY", percentage=20)
    user = _make_user(client, email="twenty@example.com")
    order = _make_order(client, user["id"], unit_price=100.00)  # 10000 cents

    resp = client.post(
        f"/orders/{order['id']}/apply-discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": code},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["subtotal"] == 10000
    assert body["discount_percentage"] == 20
    assert body["discount_amount"] == 2000
    assert body["final_total"] == 8000
    assert body["discount_code"] == "TWENTY"


# T005 — auth/access error paths

def test_apply_discount_missing_auth(client, make_discount_code):
    code = make_discount_code()
    user = _make_user(client, email="noauth@example.com")
    order = _make_order(client, user["id"])

    resp = client.post(
        f"/orders/{order['id']}/apply-discount",
        json={"code": code},
    )
    assert resp.status_code == 401


def test_apply_discount_wrong_owner(client, make_discount_code):
    code = make_discount_code(code="OWN10", percentage=10)
    owner = _make_user(client, email="realowner@example.com")
    other = _make_user(client, email="notowner@example.com")
    order = _make_order(client, owner["id"])

    resp = client.post(
        f"/orders/{order['id']}/apply-discount",
        headers={"X-User-Id": str(other["id"])},
        json={"code": code},
    )
    assert resp.status_code == 403


def test_apply_discount_order_not_found(client, make_discount_code):
    code = make_discount_code(code="NF10", percentage=10)
    user = _make_user(client, email="nfuser@example.com")

    resp = client.post(
        "/orders/99999/apply-discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": code},
    )
    assert resp.status_code == 404


# T008 — US2: invalid and inactive code error paths

def test_apply_discount_invalid_code(client):
    user = _make_user(client, email="invalid@example.com")
    order = _make_order(client, user["id"])

    resp = client.post(
        f"/orders/{order['id']}/apply-discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": "NOSUCHCODE"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid discount code"


def test_apply_discount_inactive_code(client, make_discount_code):
    code = make_discount_code(code="INACTIVE", percentage=10, is_active=False)
    user = _make_user(client, email="inactive@example.com")
    order = _make_order(client, user["id"])

    resp = client.post(
        f"/orders/{order['id']}/apply-discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": code},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Discount code is no longer active"


# T010 — US3: duplicate code guard

def test_apply_discount_already_applied(client, make_discount_code):
    code = make_discount_code(code="DUPE10", percentage=10)
    user = _make_user(client, email="dupe@example.com")
    order = _make_order(client, user["id"])

    first = client.post(
        f"/orders/{order['id']}/apply-discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": code},
    )
    assert first.status_code == 200

    second = client.post(
        f"/orders/{order['id']}/apply-discount",
        headers={"X-User-Id": str(user["id"])},
        json={"code": code},
    )
    assert second.status_code == 400
    assert second.json()["detail"] == "A discount has already been applied to this order"
