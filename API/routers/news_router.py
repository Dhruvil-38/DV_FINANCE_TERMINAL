from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from auth import get_current_user, require_role, FIRM_ROLES

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("", response_model=list[schemas.NewsOut])
def list_news(
    category: schemas.NewsCategory | None = None,
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.NewsItem)
    if category:
        q = q.filter(models.NewsItem.category == category)
    return q.order_by(models.NewsItem.published_at.desc()).limit(limit).all()


@router.post("", response_model=schemas.NewsOut)
def create_news(
    item: schemas.NewsCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    row = models.NewsItem(**item.model_dump(), created_by=user.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
