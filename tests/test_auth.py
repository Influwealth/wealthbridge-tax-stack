def test_register_and_login(client):
    r = client.post("/auth/register", json={"username": "newuser", "password": "password123"})
    assert r.status_code == 201
    assert r.json()["username"] == "newuser"
    assert r.json()["is_active"] is True

    r = client.post("/auth/token", data={"username": "newuser", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert r.json()["token_type"] == "bearer"


def test_duplicate_register(client):
    client.post("/auth/register", json={"username": "dupuser", "password": "password123"})
    r = client.post("/auth/register", json={"username": "dupuser", "password": "password123"})
    assert r.status_code == 400


def test_bad_credentials(client):
    r = client.post("/auth/token", data={"username": "noone", "password": "wrongpass"})
    assert r.status_code == 401


def test_short_password_rejected(client):
    r = client.post("/auth/register", json={"username": "shortpass", "password": "abc"})
    assert r.status_code == 422
