import models


def test_login_returns_token_and_profile(client, make_user):
    user = make_user(role="analyst", email="analyst@dvfinance.test", password="Analyst@123")

    response = client.post("/api/auth/login", json={"email": "analyst@dvfinance.test",
                                                    "password": "Analyst@123"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "analyst"
    assert body["user_id"] == user.id
    assert body["client_id"] is None
    assert body["access_token"]


def test_login_normalizes_email_case_and_whitespace(client, make_user):
    make_user(role="admin", email="admin@dvfinance.test", password="Admin@123")

    response = client.post("/api/auth/login", json={"email": "  ADMIN@DVFinance.test  ",
                                                    "password": "Admin@123"})

    assert response.status_code == 200


def test_login_rejects_wrong_password(client, make_user):
    make_user(role="admin", email="admin@dvfinance.test", password="Admin@123")

    response = client.post("/api/auth/login", json={"email": "admin@dvfinance.test",
                                                    "password": "nope"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_rejects_disabled_account(client, make_user):
    make_user(role="staff", email="disabled@dvfinance.test", password="Staff@123", is_active=False)

    response = client.post("/api/auth/login", json={"email": "disabled@dvfinance.test",
                                                    "password": "Staff@123"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is disabled"


def test_login_rejects_unknown_email(client):
    response = client.post("/api/auth/login", json={"email": "nobody@dvfinance.test",
                                                    "password": "whatever"})

    assert response.status_code == 401


def test_client_login_records_engagement_event(client, db, make_user, make_client_record):
    record = make_client_record()
    make_user(role="client", email="client@dvfinance.test", password="Client@123", client_id=record.id)

    response = client.post("/api/auth/login", json={"email": "client@dvfinance.test",
                                                    "password": "Client@123"})

    assert response.status_code == 200
    assert response.json()["client_id"] == record.id
    events = db.query(models.EngagementEvent).all()
    assert [(e.client_id, e.event_type) for e in events] == [(record.id, "LOGIN")]


def test_firm_login_records_no_engagement_event(client, db, make_user):
    make_user(role="staff", email="staff@dvfinance.test", password="Staff@123")

    client.post("/api/auth/login", json={"email": "staff@dvfinance.test", "password": "Staff@123"})

    assert db.query(models.EngagementEvent).count() == 0


def test_me_returns_current_user(client, as_role):
    user, headers = as_role("staff")

    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"id": user.id, "name": user.name, "email": user.email,
                               "role": "staff", "client_id": None}


def test_me_requires_authentication(client):
    assert client.get("/api/auth/me").status_code == 401
