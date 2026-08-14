from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from crud import create_row
from database import get_db
from auth import get_current_user, require_role, FIRM_ROLES

router = APIRouter(prefix="/api/research-notes", tags=["research"])


@router.get("", response_model=list[schemas.ResearchNoteOut])
def list_notes(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.ResearchNote)
    if user.role == "client":
        q = q.filter(models.ResearchNote.client_id == user.client_id)
    elif client_id is not None:
        q = q.filter(models.ResearchNote.client_id == client_id)
    return q.order_by(models.ResearchNote.created_at.desc()).all()


@router.post("", response_model=schemas.ResearchNoteOut)
def create_note(
    note: schemas.ResearchNoteCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    return create_row(db, models.ResearchNote, note, created_by=user.name)
