import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import models
from database import get_db
from auth import get_current_user, require_role, FIRM_ROLES

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/export")
def export_report(
    type: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if type == "calls":
        rows = db.query(models.TradeCall).all()
        df = pd.DataFrame([{
            "id": r.id, "symbol": r.symbol, "sector": r.sector, "direction": r.direction,
            "entry": r.entry, "stop_loss": r.stop_loss, "target": r.target,
            "status": r.status, "result_pct": r.result_pct,
            "created_at": r.created_at, "closed_at": r.closed_at,
        } for r in rows])
    elif type == "clients":
        if user.role == "client":
            raise HTTPException(status_code=403, detail="Not permitted")
        rows = db.query(models.Client).all()
        df = pd.DataFrame([{
            "id": c.id, "name": c.name, "email": c.email, "tier": c.tier,
            "status": c.status, "assigned_analyst": c.assigned_analyst,
            "aum": c.aum, "joined_at": c.joined_at,
        } for c in rows])
    elif type == "performance":
        rows = db.query(models.TradeCall).filter(models.TradeCall.result_pct.isnot(None)).all()
        df = pd.DataFrame([{
            "symbol": r.symbol, "sector": r.sector, "status": r.status,
            "result_pct": r.result_pct, "closed_at": r.closed_at,
        } for r in rows])
    else:
        raise HTTPException(status_code=400, detail="type must be one of: calls, clients, performance")

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=dvfinance_{type}_report.csv"},
    )
