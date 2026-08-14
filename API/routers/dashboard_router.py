from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def iso_z(value: datetime) -> str:
    """UTC timestamp in the Z-suffixed form the frontend parses."""
    return value.isoformat() + "Z"


def feed_entries(db: Session, model, timestamp_column, kind: str, to_entry, limit: int = 5) -> list[dict]:
    """Latest rows of one activity-feed source, tagged with its entry type."""
    rows = db.query(model).order_by(timestamp_column.desc()).limit(limit).all()
    return [{"type": kind, **to_entry(row)} for row in rows]


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    q = db.query(models.TradeCall)
    if user.role == "client":
        # clients see the firm's overall call performance, not internal ops metrics
        pass

    total_calls = q.count()
    active_calls = q.filter(models.TradeCall.status == "ACTIVE").count()
    target_hits = q.filter(models.TradeCall.status == "TARGET_HIT").count()
    sl_hits = q.filter(models.TradeCall.status == "SL_HIT").count()
    closed = target_hits + sl_hits
    win_rate = round((target_hits / closed) * 100, 1) if closed else 0.0

    avg_result = db.query(func.avg(models.TradeCall.result_pct)).filter(
        models.TradeCall.result_pct.isnot(None)
    ).scalar() or 0.0

    cards = [
        {"label": "Active Calls", "value": active_calls, "trend": None, "kind": "neutral"},
        {"label": "Win Rate", "value": f"{win_rate}%", "trend": "up" if win_rate >= 50 else "down", "kind": "rate"},
        {"label": "Avg Result / Call", "value": f"{round(avg_result, 2)}%", "trend": "up" if avg_result >= 0 else "down", "kind": "rate"},
        {"label": "Total Calls (All-Time)", "value": total_calls, "trend": None, "kind": "neutral"},
    ]

    if user.role != "client":
        clients_total = db.query(models.Client).count()
        clients_active = db.query(models.Client).filter(models.Client.status == "Active").count()
        cards.append({"label": "Active Clients", "value": f"{clients_active}/{clients_total}", "trend": None, "kind": "neutral"})
        open_tasks = db.query(models.Task).filter(models.Task.status != "DONE").count()
        cards.append({"label": "Open Tasks", "value": open_tasks, "trend": None, "kind": "neutral"})
    else:
        client = db.query(models.Client).filter(models.Client.id == user.client_id).first()
        if client:
            cards.append({"label": "Portfolio AUM", "value": f"₹{client.aum:,.0f}", "trend": None, "kind": "neutral"})
            cards.append({"label": "Account Tier", "value": client.tier, "trend": None, "kind": "neutral"})

    return {"cards": cards, "generated_at": iso_z(datetime.utcnow())}


@router.get("/call-performance")
def call_performance(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Small rolling call performance series for the dashboard preview chart."""
    since = datetime.utcnow() - timedelta(days=30)
    calls = (
        db.query(models.TradeCall)
        .filter(models.TradeCall.created_at >= since)
        .order_by(models.TradeCall.created_at)
        .all()
    )
    running = 0.0
    series = []
    for c in calls:
        if c.result_pct is not None:
            running += c.result_pct
        series.append({"date": c.created_at.strftime("%Y-%m-%d"), "cumulative_pct": round(running, 2)})
    return {"series": series}


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    items = (
        db.query(models.Notification)
        .filter((models.Notification.audience_role.is_(None)) | (models.Notification.audience_role == user.role))
        .order_by(models.Notification.created_at.desc())
        .limit(20)
        .all()
    )
    return {"notifications": [
        {"id": n.id, "message": n.message, "level": n.level, "created_at": iso_z(n.created_at)}
        for n in items
    ]}


@router.get("/recent-updates")
def recent_updates(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Unified activity feed across calls, news, and research notes."""
    updates = feed_entries(
        db, models.TradeCall, models.TradeCall.created_at, "call",
        lambda c: {
            "title": f"{c.direction} call opened — {c.symbol}",
            "timestamp": iso_z(c.created_at), "meta": c.status,
        },
    ) + feed_entries(
        db, models.NewsItem, models.NewsItem.published_at, "news",
        lambda n: {"title": n.title, "timestamp": iso_z(n.published_at), "meta": n.category},
    )

    if user.role != "client":
        updates += feed_entries(
            db, models.ResearchNote, models.ResearchNote.created_at, "note",
            lambda note: {"title": note.title, "timestamp": iso_z(note.created_at), "meta": note.created_by},
        )

    updates.sort(key=lambda u: u["timestamp"], reverse=True)
    return {"updates": updates[:10]}
