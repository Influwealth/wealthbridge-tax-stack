def test_create_record(client, auth_headers):
    payload = {
        "entity_name": "Acme Partners LLC",
        "tax_year": 2024,
        "income": "500000.00",
        "expenses": "150000.00",
        "entity_type": "partnership",
    }
    r = client.post("/tax/records/", json=payload, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["entity_name"] == "Acme Partners LLC"
    assert data["tax_year"] == 2024
    assert data["tax_due"] is not None


def test_list_records(client, auth_headers):
    r = client.get("/tax/records/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_record_not_found(client, auth_headers):
    r = client.get("/tax/records/999999", headers=auth_headers)
    assert r.status_code == 404


def test_update_record(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Corp Inc", "tax_year": 2024, "income": "1000000.00", "entity_type": "corporation"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]

    r = client.patch(
        f"/tax/records/{record_id}",
        json={"expenses": "200000.00"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert float(r.json()["expenses"]) == 200000.00


def test_delete_record(client, auth_headers):
    r = client.post(
        "/tax/records/",
        json={"entity_name": "Temp Corp", "tax_year": 2024, "income": "100000.00"},
        headers=auth_headers,
    )
    record_id = r.json()["id"]

    r = client.delete(f"/tax/records/{record_id}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/tax/records/{record_id}", headers=auth_headers)
    assert r.status_code == 404


def test_requires_auth(client):
    r = client.get("/tax/records/")
    assert r.status_code == 401
