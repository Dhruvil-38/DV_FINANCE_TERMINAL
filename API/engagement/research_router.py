from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db, commit_session
from auth import get_current_user, require_role, FIRM_ROLES

router = APIRouter(prefix="/api/research-notes", tags=["research"])


@router.get("", response_model=list[schemas.ResearchNoteOut])
def list_notes(
    client_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.ResearchNote)
    if user.role == "client":
        # A client account with no linked client record must not fall through to
        # firm-wide notes (client_id IS NULL) — scope it to nothing instead.
        if user.client_id is None:
            return []
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
    row = models.ResearchNote(**note.model_dump(), created_by=user.name)
    db.add(row)
    commit_session(db, conflict_detail="Could not save this note — check the linked client and call")
    db.refresh(row)
    return row
