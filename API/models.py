from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin | analyst | staff | client
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="user", foreign_keys=[client_id])


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    tier = Column(String, default="Standard")  # Standard | Premium | Institutional
    status = Column(String, default="Active")   # Active | Onboarding | Dormant
    assigned_analyst = Column(String, nullable=True)
    aum = Column(Float, default=0.0)
    joined_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="client", uselist=False, foreign_keys=[User.client_id])


class TradeCall(Base):
    __tablename__ = "trade_calls"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    sector = Column(String, nullable=False, default="Unclassified")
    direction = Column(String, nullable=False)  # LONG | SHORT
    entry = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE | TARGET_HIT | SL_HIT | CLOSED | CANCELLED
    notes = Column(Text, default="")
    result_pct = Column(Float, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    sector = Column(String, default="Unclassified")
    last_price = Column(Float, default=0.0)
    day_change_pct = Column(Float, default=0.0)
    added_by = Column(String, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)


class NewsItem(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)  # MARKET | COMPANY | FIRM
    title = Column(String, nullable=False)
    body = Column(Text, default="")
    source = Column(String, default="DV Finance Desk")
    created_by = Column(String, nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow)


class ResearchNote(Base):
    __tablename__ = "research_notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, default="")
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    call_id = Column(Integer, ForeignKey("trade_calls.id"), nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="TODO")       # TODO | IN_PROGRESS | DONE
    priority = Column(String, default="MEDIUM")    # LOW | MEDIUM | HIGH
    assigned_to = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    category = Column(String, default="General")  # Research | Compliance | Client | General
    size_kb = Column(Float, default=0.0)
    uploaded_by = Column(String, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    audience_role = Column(String, nullable=True)  # null = everyone
    message = Column(String, nullable=False)
    level = Column(String, default="info")  # info | warning | success | danger
    created_at = Column(DateTime, default=datetime.utcnow)


class EngagementEvent(Base):
    __tablename__ = "engagement_events"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    event_type = Column(String, nullable=False)  # LOGIN | REPORT_VIEW | DOWNLOAD | MESSAGE
    created_at = Column(DateTime, default=datetime.utcnow)
