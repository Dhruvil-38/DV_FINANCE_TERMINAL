import os
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import false
from sqlalchemy.orm import Session

import models
import schemas
from crud import create_row
from database import get_db
from auth import get_current_user, require_role, FIRM_ROLES

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".xls", ".docx", ".txt", ".png", ".jpg", ".jpeg"}
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def safe_filename(raw: str | None) -> str:
    """Strip any directory component and unsafe characters from a client filename."""
    base = os.path.basename((raw or "").replace("\\", "/").strip())
    cleaned = _UNSAFE_CHARS.sub("_", base).lstrip(".")
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return cleaned[:120]


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    q = db.query(models.Document)
    if user.role == "client":
        own_documents = (
            models.Document.client_id == user.client_id
            if user.client_id is not None
            else false()
        )
        q = q.filter(own_documents | (models.Document.category == "General"))
    return q.order_by(models.Document.uploaded_at.desc()).all()


@router.post("", response_model=schemas.DocumentOut)
def register_document(
    doc: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    """Registers document metadata without a physical file — use /upload for real bytes."""
    return create_row(db, models.Document, doc, uploaded_by=user.name)


@router.post("/upload", response_model=schemas.DocumentOut)
def upload_document(
    file: UploadFile = File(...),
    category: schemas.DocumentCategory = Form("General"),
    client_id: int | None = Form(None, ge=1),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    """Accepts a real file upload and stores it on disk under /api/uploads."""
    filename = safe_filename(file.filename)
    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{extension or 'unknown'}' is not allowed",
        )

    # Random on-disk name so uploads can never overwrite each other or existing files.
    stored_name = f"{secrets.token_hex(16)}{extension}"
    dest_path = os.path.join(UPLOAD_DIR, stored_name)
    if os.path.dirname(os.path.realpath(dest_path)) != UPLOAD_DIR:
        raise HTTPException(status_code=400, detail="Invalid filename")

    written = 0
    try:
        with open(dest_path, "wb") as out:
            while chunk := file.file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
                    )
                out.write(chunk)
    except Exception:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise

    return create_row(
        db, models.Document,
        filename=filename, category=category, size_kb=round(written / 1024, 1),
        uploaded_by=user.name, client_id=client_id,
    )
