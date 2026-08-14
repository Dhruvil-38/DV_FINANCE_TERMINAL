"""Shared fixtures: in-memory SQLite database plus a FastAPI app wired to the routers."""

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

# The application modules read DATABASE_URL at import time; keep them off the real
# dv_platform.db file so a test run never touches developer data.
os.environ["DATABASE_URL"] = "sqlite://"

import auth  # noqa: E402
import models  # noqa: E402
from database import Base, get_db  # noqa: E402
from engagement import clients_router, documents_router, reports_router, research_router, tasks_router  # noqa: E402
from routers import analytics_router, auth_router, dashboard_router, market_router, news_router  # noqa: E402

ROUTER_MODULES = (
    auth_router, dashboard_router, market_router, news_router, analytics_router,
    clients_router, research_router, tasks_router, documents_router, reports_router,
)

test_engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def app(db):
    application = FastAPI()
    for module in ROUTER_MODULES:
        application.include_router(module.router)
    application.dependency_overrides[get_db] = lambda: db
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(db):
    def _make_user(role="admin", email=None, password="Secret@123", name=None, client_id=None, is_active=True):
        user = models.User(
            name=name or f"{role.title()} User",
            email=email or f"{role}@dvfinance.test",
            hashed_password=auth.hash_password(password),
            role=role,
            client_id=client_id,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make_user


@pytest.fixture
def auth_headers():
    def _auth_headers(user):
        token = auth.create_access_token({"sub": str(user.id), "role": user.role})
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture
def as_role(client, make_user, auth_headers):
    """Returns a callable giving (user, headers) for a freshly created user of `role`."""

    def _as_role(role="admin", **kwargs):
        user = make_user(role=role, **kwargs)
        return user, auth_headers(user)

    return _as_role


@pytest.fixture
def make_client_record(db):
    def _make_client_record(name="Meera Kulkarni", tier="Premium", status="Active", aum=1_000_000.0):
        record = models.Client(
            name=name, email=f"{name.split()[0].lower()}@example.com",
            tier=tier, status=status, aum=aum, assigned_analyst="R. Shah",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    return _make_client_record


@pytest.fixture
def make_call(db):
    def _make_call(symbol="RELIANCE", sector="Energy", direction="LONG", status="ACTIVE",
                   result_pct=None, created_at=None, closed_at=None, entry=100.0):
        call = models.TradeCall(
            symbol=symbol, sector=sector, direction=direction, entry=entry,
            stop_loss=entry * 0.95, target=entry * 1.1, status=status,
            result_pct=result_pct, created_by="Rohan Shah",
        )
        if created_at is not None:
            call.created_at = created_at
        if closed_at is not None:
            call.closed_at = closed_at
        db.add(call)
        db.commit()
        db.refresh(call)
        return call

    return _make_call
