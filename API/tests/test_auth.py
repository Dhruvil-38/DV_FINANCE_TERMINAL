from datetime import datetime, timedelta

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from jose import jwt

import auth
import models


def test_hash_password_is_salted_and_verifiable():
    first = auth.hash_password("Secret@123")
    second = auth.hash_password("Secret@123")

    assert first != second
    assert auth.verify_password("Secret@123", first)
    assert not auth.verify_password("wrong", first)


def test_create_access_token_embeds_claims_and_expiry():
    before = datetime.utcnow()
    token = auth.create_access_token({"sub": "7", "role": "analyst"}, expires_minutes=30)

    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "7"
    assert payload["role"] == "analyst"
    expires_in = datetime.utcfromtimestamp(payload["exp"]) - before
    assert timedelta(minutes=29) <= expires_in <= timedelta(minutes=31)


def _protected_app(dependency):
    app = FastAPI()

    @app.get("/probe")
    def probe(user: models.User = Depends(dependency)):
        return {"id": user.id, "role": user.role}

    return app


@pytest.fixture
def probe_client(db):
    from database import get_db

    def _probe_client(dependency):
        app = _protected_app(dependency)
        app.dependency_overrides[get_db] = lambda: db
        return TestClient(app)

    return _probe_client


def test_get_current_user_returns_user_for_valid_token(probe_client, make_user, auth_headers):
    user = make_user(role="analyst")

    response = probe_client(auth.get_current_user).get("/probe", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {"id": user.id, "role": "analyst"}


def test_get_current_user_rejects_missing_token(probe_client):
    assert probe_client(auth.get_current_user).get("/probe").status_code == 401


def test_get_current_user_rejects_malformed_token(probe_client):
    response = probe_client(auth.get_current_user).get(
        "/probe", headers={"Authorization": "Bearer not-a-jwt"}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_get_current_user_rejects_token_without_subject(probe_client):
    token = auth.create_access_token({"role": "admin"})

    response = probe_client(auth.get_current_user).get(
        "/probe", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_get_current_user_rejects_expired_token(probe_client, make_user):
    user = make_user(role="admin")
    token = auth.create_access_token({"sub": str(user.id)}, expires_minutes=-1)

    response = probe_client(auth.get_current_user).get(
        "/probe", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_get_current_user_rejects_unknown_user(probe_client, auth_headers):
    ghost = models.User(id=4242, name="Ghost", email="ghost@dvfinance.test",
                        hashed_password="x", role="admin")

    response = probe_client(auth.get_current_user).get("/probe", headers=auth_headers(ghost))

    assert response.status_code == 401


def test_get_current_user_rejects_deactivated_user(probe_client, make_user, auth_headers):
    user = make_user(role="staff", is_active=False)

    response = probe_client(auth.get_current_user).get("/probe", headers=auth_headers(user))

    assert response.status_code == 401


def test_require_role_allows_listed_role(probe_client, make_user, auth_headers):
    user = make_user(role="analyst")

    response = probe_client(auth.require_role("admin", "analyst")).get(
        "/probe", headers=auth_headers(user)
    )

    assert response.status_code == 200


def test_require_role_blocks_other_roles(probe_client, make_user, auth_headers):
    user = make_user(role="client")

    response = probe_client(auth.require_role(*auth.FIRM_ROLES)).get(
        "/probe", headers=auth_headers(user)
    )

    assert response.status_code == 403
    assert "client" in response.json()["detail"]


def test_require_role_guard_can_be_called_directly(make_user):
    guard = auth.require_role("admin")
    admin = make_user(role="admin")
    staff = make_user(role="staff")

    assert guard(user=admin) is admin
    with pytest.raises(HTTPException) as excinfo:
        guard(user=staff)
    assert excinfo.value.status_code == 403


def test_firm_roles_excludes_clients():
    assert auth.FIRM_ROLES == ("admin", "analyst", "staff")
    assert "client" not in auth.FIRM_ROLES
