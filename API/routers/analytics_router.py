from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from database import get_db
from auth import get_current_user, require_role, FIRM_ROLES

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _calls_dataframe(db: Session) -> pd.DataFrame:
    rows = db.query(models.TradeCall).all()
    if not rows:
        return pd.DataFrame(columns=[
            "id", "symbol", "sector", "direction", "entry", "stop_loss", "target",
            "status", "result_pct", "created_at", "closed_at",
        ])
    return pd.DataFrame([{
        "id": r.id, "symbol": r.symbol, "sector": r.sector, "direction": r.direction,
        "entry": r.entry, "stop_loss": r.stop_loss, "target": r.target,
        "status": r.status, "result_pct": r.result_pct,
        "created_at": r.created_at, "closed_at": r.closed_at,
    } for r in rows])


@router.get("/win-rate")
def win_rate(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    df = _calls_dataframe(db)
    closed = df[df["status"].isin(["TARGET_HIT", "SL_HIT"])]
    if closed.empty:
        return {"win_rate_pct": 0.0, "wins": 0, "losses": 0, "total_closed": 0}
    wins = int((closed["status"] == "TARGET_HIT").sum())
    losses = int((closed["status"] == "SL_HIT").sum())
    return {
        "win_rate_pct": round(wins / len(closed) * 100, 2),
        "wins": wins,
        "losses": losses,
        "total_closed": int(len(closed)),
    }


@router.get("/accuracy")
def accuracy(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Accuracy = share of closed calls that ended net-positive, regardless of exact SL/target tag."""
    df = _calls_dataframe(db)
    closed = df[df["result_pct"].notna()]
    if closed.empty:
        return {"accuracy_pct": 0.0, "sample_size": 0, "avg_result_pct": 0.0, "std_dev_pct": 0.0}
    profitable = int((closed["result_pct"] > 0).sum())
    return {
        "accuracy_pct": round(profitable / len(closed) * 100, 2),
        "sample_size": int(len(closed)),
        "avg_result_pct": round(float(closed["result_pct"].mean()), 2),
        "std_dev_pct": round(float(closed["result_pct"].std(ddof=0) or 0.0), 2),
    }


@router.get("/monthly-performance")
def monthly_performance(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    df = _calls_dataframe(db)
    closed = df[df["result_pct"].notna()].copy()
    if closed.empty:
        return {"months": []}
    closed["month"] = closed["closed_at"].fillna(closed["created_at"]).dt.strftime("%Y-%m")
    grouped = closed.groupby("month").agg(
        avg_result_pct=("result_pct", "mean"),
        total_result_pct=("result_pct", "sum"),
        calls=("id", "count"),
    ).reset_index().sort_values("month")
    grouped[["avg_result_pct", "total_result_pct"]] = grouped[["avg_result_pct", "total_result_pct"]].round(2)
    return {"months": grouped.to_dict(orient="records")}


@router.get("/sector-performance")
def sector_performance(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    df = _calls_dataframe(db)
    if df.empty:
        return {"sectors": []}
    closed = df[df["result_pct"].notna()]
    grouped_all = df.groupby("sector").agg(total_calls=("id", "count")).reset_index()

    if closed.empty:
        grouped_all["avg_result_pct"] = 0.0
        grouped_all["win_rate_pct"] = 0.0
    else:
        perf = closed.groupby("sector").agg(
            avg_result_pct=("result_pct", "mean"),
            wins=("status", lambda s: (s == "TARGET_HIT").sum()),
            decided=("status", lambda s: s.isin(["TARGET_HIT", "SL_HIT"]).sum()),
        ).reset_index()
        perf["win_rate_pct"] = np.where(perf["decided"] > 0, perf["wins"] / perf["decided"] * 100, 0.0)
        grouped_all = grouped_all.merge(perf[["sector", "avg_result_pct", "win_rate_pct"]], on="sector", how="left").fillna(0)

    grouped_all[["avg_result_pct", "win_rate_pct"]] = grouped_all[["avg_result_pct", "win_rate_pct"]].round(2)
    return {"sectors": grouped_all.sort_values("avg_result_pct", ascending=False).to_dict(orient="records")}


@router.get("/call-history")
def call_history(limit: int = 50, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    df = _calls_dataframe(db)
    if df.empty:
        return {"history": []}
    df = df.sort_values("created_at").tail(limit).copy()
    df["cumulative_pct"] = df["result_pct"].fillna(0).cumsum().round(2)
    df["created_at"] = df["created_at"].dt.strftime("%Y-%m-%d")
    df = df[["id", "symbol", "sector", "status", "result_pct", "cumulative_pct", "created_at"]]
    df = df.astype(object).where(df.notna(), None)  # NaN -> None so it serializes as JSON null
    return {"history": df.to_dict(orient="records")}


@router.get("/client-engagement")
def client_engagement(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    clients = db.query(models.Client).all()
    events = db.query(models.EngagementEvent).all()
    if not clients:
        return {"clients": []}

    ev_df = pd.DataFrame([{"client_id": e.client_id, "event_type": e.event_type} for e in events]) \
        if events else pd.DataFrame(columns=["client_id", "event_type"])

    weight = {"LOGIN": 1, "REPORT_VIEW": 2, "DOWNLOAD": 2, "MESSAGE": 3}

    results = []
    for c in clients:
        c_events = ev_df[ev_df["client_id"] == c.id] if not ev_df.empty else ev_df
        counts = c_events["event_type"].value_counts().to_dict() if not c_events.empty else {}
        score = sum(counts.get(k, 0) * w for k, w in weight.items())
        results.append({
            "client_id": c.id,
            "client_name": c.name,
            "tier": c.tier,
            "total_events": int(len(c_events)),
            "engagement_score": int(score),
            "breakdown": {k: int(counts.get(k, 0)) for k in weight},
        })

    results.sort(key=lambda r: r["engagement_score"], reverse=True)
    return {"clients": results}
