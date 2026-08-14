import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import models
from database import get_db
from auth import get_current_user, require_role, FIRM_ROLES

router = APIRouter(prefix="/api/reports", tags=["reports"])

REPORT_COLUMNS = {
    "calls": ["id", "symbol", "sector", "direction", "entry", "stop_loss", "target",
              "status", "result_pct", "created_at", "closed_at"],
    "clients": ["id", "name", "email", "tier", "status", "assigned_analyst", "aum", "joined_at"],
    "performance": ["symbol", "sector", "status", "result_pct", "closed_at"],
}

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _defuse_formulas(df: pd.DataFrame) -> pd.DataFrame:
    """Neutralise spreadsheet formula injection in exported text columns."""
    for column in df.select_dtypes(include="object").columns:
        df[column] = df[column].map(
            lambda v: f"'{v}" if isinstance(v, str) and v.startswith(_FORMULA_PREFIXES) else v
        )
    return df


@router.get("/export")
def export_report(
    type: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if type not in REPORT_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=f"type must be one of: {', '.join(REPORT_COLUMNS)}",
        )

    if type == "calls":
        rows = db.query(models.TradeCall).all()
        records = [{
            "id": r.id, "symbol": r.symbol, "sector": r.sector, "direction": r.direction,
            "entry": r.entry, "stop_loss": r.stop_loss, "target": r.target,
            "status": r.status, "result_pct": r.result_pct,
            "created_at": r.created_at, "closed_at": r.closed_at,
        } for r in rows]
    elif type == "clients":
        if user.role == "client":
            raise HTTPException(status_code=403, detail="Not permitted")
        rows = db.query(models.Client).all()
        records = [{
            "id": c.id, "name": c.name, "email": c.email, "tier": c.tier,
            "status": c.status, "assigned_analyst": c.assigned_analyst,
            "aum": c.aum, "joined_at": c.joined_at,
        } for c in rows]
    else:
        rows = db.query(models.TradeCall).filter(models.TradeCall.result_pct.isnot(None)).all()
        records = [{
            "symbol": r.symbol, "sector": r.sector, "status": r.status,
            "result_pct": r.result_pct, "closed_at": r.closed_at,
        } for r in rows]

    # Explicit columns keep an empty export a valid header-only CSV instead of a blank file.
    df = pd.DataFrame(records, columns=REPORT_COLUMNS[type])

    buffer = io.StringIO()
    _defuse_formulas(df).to_csv(buffer, index=False)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=dvfinance_{type}_report.csv"},
    )
