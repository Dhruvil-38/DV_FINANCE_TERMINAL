import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import auth
import models
import seed


@pytest.fixture
def seed_env(monkeypatch):
    """Points seed.run() at a throwaway in-memory database."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(seed, "engine", engine)
    monkeypatch.setattr(seed, "SessionLocal", SessionLocal)
    yield engine, SessionLocal
    engine.dispose()


def test_run_creates_tables(seed_env):
    engine, _ = seed_env

    seed.run()

    tables = set(inspect(engine).get_table_names())
    assert {"users", "clients", "trade_calls", "watchlist", "news", "research_notes",
            "tasks", "documents", "notifications", "engagement_events"} <= tables


def test_run_seeds_demo_users_with_hashed_passwords(seed_env):
    _, SessionLocal = seed_env

    seed.run()

    session = SessionLocal()
    try:
        users = session.query(models.User).all()
        by_email = {u.email: u for u in users}
        assert set(by_email) == {"admin@dvfinance.in", "analyst@dvfinance.in",
                                 "staff@dvfinance.in", "client@dvfinance.in"}
        assert {u.role for u in users} == {"admin", "analyst", "staff", "client"}
        admin = by_email["admin@dvfinance.in"]
        assert admin.hashed_password != "Admin@123"
        assert auth.verify_password("Admin@123", admin.hashed_password)
        assert by_email["client@dvfinance.in"].client_id is not None
    finally:
        session.close()


def test_run_seeds_demo_content(seed_env):
    _, SessionLocal = seed_env

    seed.run()

    session = SessionLocal()
    try:
        assert session.query(models.Client).count() == 5
        for model in (models.TradeCall, models.WatchlistItem, models.NewsItem,
                      models.ResearchNote, models.Task, models.Document,
                      models.Notification, models.EngagementEvent):
            assert session.query(model).count() > 0, model.__name__
    finally:
        session.close()


def test_run_is_idempotent(seed_env):
    _, SessionLocal = seed_env

    seed.run()
    seed.run()

    session = SessionLocal()
    try:
        assert session.query(models.User).count() == 4
        assert session.query(models.Client).count() == 5
    finally:
        session.close()
