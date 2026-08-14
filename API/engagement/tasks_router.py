from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from crud import create_row, get_or_404, update_row
from database import get_db
from auth import require_role, FIRM_ROLES

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db), user: models.User = Depends(require_role(*FIRM_ROLES))):
    return db.query(models.Task).order_by(models.Task.due_date.asc().nulls_last()).all()


@router.post("", response_model=schemas.TaskOut)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db), user: models.User = Depends(require_role(*FIRM_ROLES))):
    return create_row(db, models.Task, task)


@router.patch("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    row = get_or_404(db, models.Task, task_id, "Task not found")
    return update_row(db, row, payload)
