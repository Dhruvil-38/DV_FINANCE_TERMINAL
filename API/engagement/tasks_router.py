from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db, commit_session
from auth import require_role, FIRM_ROLES

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

TASK_STATUSES = ("TODO", "IN_PROGRESS", "DONE")
TASK_PRIORITIES = ("LOW", "MEDIUM", "HIGH")


def _validate(status: str | None, priority: str | None) -> None:
    """Unknown values used to be stored as-is, silently hiding the task from every board column."""
    if status is not None and status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(TASK_STATUSES)}")
    if priority is not None and priority not in TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"priority must be one of: {', '.join(TASK_PRIORITIES)}")


@router.get("", response_model=list[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db), user: models.User = Depends(require_role(*FIRM_ROLES))):
    return db.query(models.Task).order_by(models.Task.due_date.asc().nulls_last()).all()


@router.post("", response_model=schemas.TaskOut)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db), user: models.User = Depends(require_role(*FIRM_ROLES))):
    _validate(task.status, task.priority)
    row = models.Task(**task.model_dump())
    db.add(row)
    commit_session(db, conflict_detail="Could not create this task")
    db.refresh(row)
    return row


@router.patch("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(*FIRM_ROLES)),
):
    row = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    _validate(payload.status, payload.priority)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    commit_session(db, conflict_detail="Could not update this task")
    db.refresh(row)
    return row
