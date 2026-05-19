def test_create_user(client):
    resp = client.post(
        "/users", json={"email": "alice@example.com", "name": "Alice"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] >= 1
    assert body["email"] == "alice@example.com"


def test_create_user_duplicate_email(client):
    client.post("/users", json={"email": "bob@example.com", "name": "Bob"})
    resp = client.post("/users", json={"email": "bob@example.com", "name": "Bob 2"})
    assert resp.status_code == 409


def test_get_user(client):
    create = client.post(
        "/users", json={"email": "carol@example.com", "name": "Carol"}
    ).json()
    resp = client.get(f"/users/{create['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Carol"


def test_get_user_not_found(client):
    resp = client.get("/users/99999")
    assert resp.status_code == 404
