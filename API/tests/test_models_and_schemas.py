from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

import models
import schemas


def test_user_defaults_and_timestamps(db):
    user = models.User(name="Aditi Shah", email="aditi@dvfinance.test",
                       hashed_password="hash", role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.is_active is True
    assert isinstance(user.created_at, datetime)


def test_user_email_is_unique(db):
    db.add(models.User(name="A", email="dup@dvfinance.test", hashed_password="h", role="admin"))
    db.commit()

    db.add(models.User(name="B", email="dup@dvfinance.test", hashed_password="h", role="staff"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_user_client_relationship_is_bidirectional(db, make_client_record):
    record = make_client_record(name="Meera Kulkarni")
    user = models.User(name=record.name, email="meera@dvfinance.test",
                       hashed_password="h", role="client", client_id=record.id)
    db.add(user)
    db.commit()
    db.refresh(record)

    assert user.client.id == record.id
    assert record.user.id == user.id


def test_client_column_defaults(db):
    record = models.Client(name="Priya Nair", email="priya@example.com")
    db.add(record)
    db.commit()
    db.refresh(record)

    assert record.tier == "Standard"
    assert record.status == "Active"
    assert record.aum == 0.0


def test_trade_call_defaults(db):
    call = models.TradeCall(symbol="TCS", direction="LONG", entry=100.0,
                            stop_loss=95.0, target=110.0, created_by="R. Shah")
    db.add(call)
    db.commit()
    db.refresh(call)

    assert call.status == "ACTIVE"
    assert call.sector == "Unclassified"
    assert call.notes == ""
    assert call.result_pct is None
    assert call.closed_at is None


def test_task_and_document_defaults(db):
    task = models.Task(title="Prepare deck")
    document = models.Document(filename="note.pdf", uploaded_by="R. Shah")
    db.add_all([task, document])
    db.commit()
    db.refresh(task)
    db.refresh(document)

    assert (task.status, task.priority) == ("TODO", "MEDIUM")
    assert (document.category, document.size_kb) == ("General", 0.0)


def test_notification_defaults_to_broadcast_info(db):
    notification = models.Notification(message="Market closed early")
    db.add(notification)
    db.commit()
    db.refresh(notification)

    assert notification.audience_role is None
    assert notification.level == "info"


def test_engagement_event_requires_client(db):
    db.add(models.EngagementEvent(event_type="LOGIN"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_login_request_requires_both_fields():
    with pytest.raises(ValidationError):
        schemas.LoginRequest(email="admin@dvfinance.test")


def test_token_response_defaults_to_bearer():
    token = schemas.TokenResponse(access_token="abc", role="admin", name="Aditi", user_id=1)

    assert token.token_type == "bearer"
    assert token.client_id is None


def test_trade_call_out_reads_from_orm_object(db, make_call):
    call = make_call(symbol="ONGC", status="TARGET_HIT", result_pct=3.5)

    out = schemas.TradeCallOut.model_validate(call)

    assert out.symbol == "ONGC"
    assert out.result_pct == 3.5
    assert out.created_by == "Rohan Shah"


def test_client_out_reads_from_orm_object(make_client_record):
    record = make_client_record(name="Arjun Verma", tier="Premium")

    out = schemas.ClientOut.model_validate(record)

    assert out.name == "Arjun Verma"
    assert out.tier == "Premium"
    assert isinstance(out.joined_at, datetime)


def test_trade_call_update_tracks_unset_fields():
    payload = schemas.TradeCallUpdate(status="CLOSED")

    assert payload.model_dump(exclude_unset=True) == {"status": "CLOSED"}
    assert payload.model_dump() == {"status": "CLOSED", "notes": None, "result_pct": None}


def test_schema_defaults_for_creation_payloads():
    assert schemas.WatchlistCreate(symbol="TCS").model_dump() == {
        "symbol": "TCS", "sector": "Unclassified", "last_price": 0.0, "day_change_pct": 0.0,
    }
    assert schemas.NewsCreate(category="MARKET", title="t").source == "DV Finance Desk"
    assert schemas.DocumentCreate(filename="a.pdf").category == "General"
    assert schemas.ResearchNoteCreate(title="t").client_id is None


def test_trade_call_create_requires_numeric_levels():
    with pytest.raises(ValidationError):
        schemas.TradeCallCreate(symbol="TCS", direction="LONG", entry="not-a-number",
                                stop_loss=95.0, target=110.0)
