"""
Shared single-row database helpers.

Every router created, fetched, and patched rows with the same
add/commit/refresh, filter-by-id + 404, and field-copy blocks; those live here
instead of being repeated per module.
"""

from typing import Optional, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base

ModelT = TypeVar("ModelT", bound=Base)


def save(db: Session, row: ModelT) -> ModelT:
    """Persists a new or mutated row and returns it with server defaults loaded."""
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_row(db: Session, model: type[ModelT], payload: Optional[BaseModel] = None, **extra) -> ModelT:
    """Builds a row from a Pydantic payload plus server-side fields, then saves it."""
    fields = payload.model_dump() if payload is not None else {}
    return save(db, model(**fields, **extra))


def get_or_404(db: Session, model: type[ModelT], row_id: int, detail: str) -> ModelT:
    row = db.query(model).filter(model.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=detail)
    return row


def apply_fields(row: ModelT, payload: BaseModel, exclude_unset: bool = True) -> ModelT:
    """Copies the supplied payload fields onto an existing row without saving."""
    for field, value in payload.model_dump(exclude_unset=exclude_unset).items():
        setattr(row, field, value)
    return row


def update_row(db: Session, row: ModelT, payload: BaseModel, exclude_unset: bool = True) -> ModelT:
    return save(db, apply_fields(row, payload, exclude_unset))
