from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from auth import require_role, FIRM_ROLES

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=list[schemas.ClientOut])
def list_clients(db: Session = Depends(get_db), user: models.User = Depends(require_role(*FIRM_ROLES))):
    return db.query(models.Client).order_by(models.Client.name).all()


@router.get("/{client_id}", response_model=schemas.ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db), user: models.User = Depends(require_role(*FIRM_ROLES))):
    row = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    return row


@router.post("", response_model=schemas.ClientOut)
def create_client(
    client: schemas.ClientCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("admin", "analyst")),
):
    row = models.Client(**client.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{client_id}", response_model=schemas.ClientOut)
def update_client(
    client_id: int,
    payload: schemas.ClientCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("admin", "analyst")),
):
    row = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
