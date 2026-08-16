from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from crud import create_row, get_or_404, update_row
from database import get_db
from auth import require_role, FIRM_ROLES

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=list[schemas.ClientOut])
def list_clients(db: Session = Depends(get_db), user: models.User = Depends(require_role(*FIRM_ROLES))):
    return db.query(models.Client).order_by(models.Client.name).all()


@router.get("/{client_id}", response_model=schemas.ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db), user: models.User = Depends(require_role(*FIRM_ROLES))):
    return get_or_404(db, models.Client, client_id, "Client not found")


@router.post("", response_model=schemas.ClientOut)
def create_client(
    client: schemas.ClientCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("admin", "analyst")),
):
    return create_row(db, models.Client, client)


@router.patch("/{client_id}", response_model=schemas.ClientOut)
def update_client(
    client_id: int,
    payload: schemas.ClientCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role("admin", "analyst")),
):
    row = get_or_404(db, models.Client, client_id, "Client not found")
    return update_row(db, row, payload, exclude_unset=False)
