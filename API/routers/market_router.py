from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
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
    row = models.WatchlistItem(**item.model_dump(), added_by=user.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/watchlist/{item_id}")
def delete_watchlist(
    item_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    row = db.query(models.WatchlistItem).filter(models.WatchlistItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    db.delete(row)
    db.commit()
    return {"deleted": item_id}


# ---------------- Trade calls ----------------

@router.get("/calls", response_model=list[schemas.TradeCallOut])
def list_calls(
    status_filter: str | None = None,
    sector: str | None = None,
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
    if call.direction not in ("LONG", "SHORT"):
        raise HTTPException(status_code=400, detail="direction must be LONG or SHORT")
    row = models.TradeCall(**call.model_dump(), created_by=user.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/calls/{call_id}", response_model=schemas.TradeCallOut)
def update_call(
    call_id: int,
    payload: schemas.TradeCallUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("admin", "analyst")),
):
    row = db.query(models.TradeCall).filter(models.TradeCall.id == call_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Trade call not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(row, field, value)

    if payload.status in ("TARGET_HIT", "SL_HIT", "CLOSED"):
        row.closed_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return row
