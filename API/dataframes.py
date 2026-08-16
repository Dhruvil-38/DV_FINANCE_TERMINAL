"""
Pandas projections of ORM rows.

Analytics and the CSV exporter flattened the same rows into the same column
sets; the record shapes and the empty-frame handling are defined once here.
"""

import pandas as pd
from sqlalchemy.orm import Session

import models

TRADE_CALL_COLUMNS = [
    "id", "symbol", "sector", "direction", "entry", "stop_loss", "target",
    "status", "result_pct", "created_at", "closed_at",
]

CLIENT_COLUMNS = [
    "id", "name", "email", "tier", "status", "assigned_analyst", "aum", "joined_at",
]

PERFORMANCE_COLUMNS = ["symbol", "sector", "status", "result_pct", "closed_at"]


def trade_call_record(call: models.TradeCall) -> dict:
    return {
        "id": call.id, "symbol": call.symbol, "sector": call.sector, "direction": call.direction,
        "entry": call.entry, "stop_loss": call.stop_loss, "target": call.target,
        "status": call.status, "result_pct": call.result_pct,
        "created_at": call.created_at, "closed_at": call.closed_at,
    }


def client_record(client: models.Client) -> dict:
    return {
        "id": client.id, "name": client.name, "email": client.email, "tier": client.tier,
        "status": client.status, "assigned_analyst": client.assigned_analyst,
        "aum": client.aum, "joined_at": client.joined_at,
    }


def dataframe(records: list[dict], columns: list[str]) -> pd.DataFrame:
    """Frame with a stable schema, so downstream column access works when empty."""
    return pd.DataFrame(records, columns=columns)


def calls_dataframe(db: Session) -> pd.DataFrame:
    rows = db.query(models.TradeCall).all()
    return dataframe([trade_call_record(r) for r in rows], TRADE_CALL_COLUMNS)


def clients_dataframe(db: Session) -> pd.DataFrame:
    rows = db.query(models.Client).all()
    return dataframe([client_record(c) for c in rows], CLIENT_COLUMNS)


def performance_dataframe(db: Session) -> pd.DataFrame:
    rows = db.query(models.TradeCall).filter(models.TradeCall.result_pct.isnot(None)).all()
    records = [{k: v for k, v in trade_call_record(r).items() if k in PERFORMANCE_COLUMNS} for r in rows]
    return dataframe(records, PERFORMANCE_COLUMNS)
