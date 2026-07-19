import os
import shutil

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from auth import get_current_user, require_role, FIRM_ROLES

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
    db.commit()
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
    dest_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    size_kb = round(os.path.getsize(dest_path) / 1024, 1)

    row = models.Document(
        filename=file.filename, category=category, size_kb=size_kb,
        uploaded_by=user.name, client_id=client_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
