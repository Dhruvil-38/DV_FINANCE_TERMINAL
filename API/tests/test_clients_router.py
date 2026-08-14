CLIENT_PAYLOAD = {
    "name": "Arjun Verma", "email": "arjun.verma@example.com", "phone": "+91 90000 44556",
    "tier": "Premium", "status": "Active", "assigned_analyst": "R. Shah", "aum": 2_180_000.0,
}


def test_list_clients_sorted_by_name(client, as_role, make_client_record):
    _, headers = as_role("staff")
    make_client_record(name="Priya Nair")
    make_client_record(name="Devika Iyer")

    response = client.get("/api/clients", headers=headers)

    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["Devika Iyer", "Priya Nair"]


def test_list_clients_forbidden_for_client_role(client, as_role):
    _, headers = as_role("client")

    assert client.get("/api/clients", headers=headers).status_code == 403


def test_get_client_returns_record(client, as_role, make_client_record):
    _, headers = as_role("staff")
    record = make_client_record(name="Meera Kulkarni")

    response = client.get(f"/api/clients/{record.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Meera Kulkarni"


def test_get_missing_client_returns_404(client, as_role):
    _, headers = as_role("admin")

    response = client.get("/api/clients/999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"


def test_create_client_persists_payload(client, as_role):
    _, headers = as_role("analyst")

    response = client.post("/api/clients", headers=headers, json=CLIENT_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Arjun Verma"
    assert body["aum"] == 2_180_000.0
    assert body["id"] > 0


def test_create_client_forbidden_for_staff(client, as_role):
    _, headers = as_role("staff")

    assert client.post("/api/clients", headers=headers, json=CLIENT_PAYLOAD).status_code == 403


def test_update_client_overwrites_fields(client, as_role, make_client_record):
    _, headers = as_role("admin")
    record = make_client_record(name="Priya Nair", tier="Standard", status="Onboarding")

    response = client.patch(f"/api/clients/{record.id}", headers=headers, json={
        **CLIENT_PAYLOAD, "name": "Priya Nair", "tier": "Institutional", "status": "Active",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "Institutional"
    assert body["status"] == "Active"
    assert body["assigned_analyst"] == "R. Shah"


def test_update_missing_client_returns_404(client, as_role):
    _, headers = as_role("admin")

    response = client.patch("/api/clients/999", headers=headers, json=CLIENT_PAYLOAD)

    assert response.status_code == 404


def test_update_client_forbidden_for_staff(client, as_role, make_client_record):
    _, headers = as_role("staff")
    record = make_client_record()

    response = client.patch(f"/api/clients/{record.id}", headers=headers, json=CLIENT_PAYLOAD)

    assert response.status_code == 403
