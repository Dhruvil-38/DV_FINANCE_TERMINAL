from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from crud import apply_fields, create_row, get_or_404, save
from database import get_db
from auth import get_current_user, require_role, FIRM_ROLES

router = APIRouter(prefix="/api/market", tags=["market"])


# ---------------- Watchlist ----------------

@router.get("/watchlist", response_model=list[schemas.WatchlistOut])
def list_watchlist(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.WatchlistItem).order_by(models.WatchlistItem.symbol).all()


@router.post("/watchlist", response_model=schemas.WatchlistOut)
def add_watchlist(
    item: schemas.WatchlistCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    return create_row(db, models.WatchlistItem, item, added_by=user.name)


@router.delete("/watchlist/{item_id}")
def delete_watchlist(
    item_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    row = get_or_404(db, models.WatchlistItem, item_id, "Watchlist item not found")
    db.delete(row)
    db.commit()
    return {"deleted": item_id}


# ---------------- Trade calls ----------------

@router.get("/calls", response_model=list[schemas.TradeCallOut])
def list_calls(
    status_filter: schemas.CallStatus | None = None,
    sector: str | None = Query(None, max_length=64),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.TradeCall)
    if status_filter:
        q = q.filter(models.TradeCall.status == status_filter)
    if sector:
        q = q.filter(models.TradeCall.sector == sector)
    return q.order_by(models.TradeCall.created_at.desc()).all()


@router.post("/calls", response_model=schemas.TradeCallOut)
def create_call(
    call: schemas.TradeCallCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("admin", "analyst")),
):
    return create_row(db, models.TradeCall, call, created_by=user.name)


@router.patch("/calls/{call_id}", response_model=schemas.TradeCallOut)
def update_call(
    call_id: int,
    payload: schemas.TradeCallUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("admin", "analyst")),
):
    row = apply_fields(get_or_404(db, models.TradeCall, call_id, "Trade call not found"), payload)

    if payload.status in ("TARGET_HIT", "SL_HIT", "CLOSED"):
        row.closed_at = datetime.utcnow()

    return save(db, row)
