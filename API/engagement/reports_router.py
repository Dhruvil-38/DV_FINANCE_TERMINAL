import io
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import models
from dataframes import calls_dataframe, clients_dataframe, performance_dataframe
from database import get_db
from auth import get_current_user, require_role, FIRM_ROLES

router = APIRouter(prefix="/api/reports", tags=["reports"])

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
    type: Literal["calls", "clients", "performance"],
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if type == "calls":
        df = calls_dataframe(db)
    elif type == "clients":
        if user.role == "client":
            raise HTTPException(status_code=403, detail="Not permitted")
        df = clients_dataframe(db)
    else:
        df = performance_dataframe(db)

    if df.empty:
        df = pd.DataFrame()  # nothing to export: stay byte-empty rather than emitting a bare header

    buffer = io.StringIO()
    _defuse_formulas(df).to_csv(buffer, index=False)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=dvfinance_{type}_report.csv"},
    )
