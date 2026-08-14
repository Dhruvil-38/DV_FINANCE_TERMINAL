import logging
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db, commit_session
from auth import get_current_user, require_role, FIRM_ROLES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    q = db.query(models.Document)
    if user.role == "client":
        q = q.filter(
            (models.Document.client_id == user.client_id) | (models.Document.category == "General")
        )
    return q.order_by(models.Document.uploaded_at.desc()).all()


@router.post("", response_model=schemas.DocumentOut)
def register_document(
    doc: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    """Registers document metadata without a physical file — use /upload for real bytes."""
    row = models.Document(**doc.model_dump(), uploaded_by=user.name)
    db.add(row)
    commit_session(db, conflict_detail="Could not register this document")
    db.refresh(row)
    return row


@router.post("/upload", response_model=schemas.DocumentOut)
def upload_document(
    file: UploadFile = File(...),
    category: str = Form("General"),
    client_id: int | None = Form(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    """Accepts a real file upload and stores it on disk under /api/uploads."""
    filename = os.path.basename((file.filename or "").strip())
    if not filename or filename in (".", ".."):
        raise HTTPException(status_code=400, detail="A filename is required")

    dest_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(dest_path, "wb") as out:
            shutil.copyfileobj(file.file, out)
        size_kb = round(os.path.getsize(dest_path) / 1024, 1)
    except OSError as exc:
        # A half-written file on disk with no database row is worse than a clear error.
        _discard(dest_path)
        logger.exception("Storing upload %r failed", filename)
        raise HTTPException(status_code=500, detail="Could not store the uploaded file") from exc
    finally:
        file.file.close()

    row = models.Document(
        filename=filename, category=category, size_kb=size_kb,
        uploaded_by=user.name, client_id=client_id,
    )
    db.add(row)
    try:
        commit_session(db, conflict_detail="Could not record this document — check the linked client")
    except HTTPException:
        _discard(dest_path)
        raise
    db.refresh(row)
    return row


def _discard(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning("Could not clean up partial upload at %s", path, exc_info=True)
