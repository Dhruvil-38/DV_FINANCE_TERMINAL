import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import models
from dataframes import calls_dataframe, clients_dataframe, performance_dataframe
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
        df = calls_dataframe(db)
    elif type == "clients":
        if user.role == "client":
            raise HTTPException(status_code=403, detail="Not permitted")
        df = clients_dataframe(db)
    elif type == "performance":
        df = performance_dataframe(db)
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
