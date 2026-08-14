import logging
import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from auth import verify_password, create_access_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Per-process fixed-window throttle on failed logins. Enough to blunt credential
# stuffing on a single instance; front a shared store (Redis) or WAF rule when
# running multiple workers.
LOGIN_MAX_ATTEMPTS = int(os.environ.get("DV_LOGIN_MAX_ATTEMPTS", "10"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("DV_LOGIN_WINDOW_SECONDS", "300"))

_failed_attempts: dict[str, list[float]] = defaultdict(list)
_attempts_lock = Lock()


def _throttle_key(request: Request, email: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}|{email}"


def _check_login_throttle(key: str) -> None:
    cutoff = time.monotonic() - LOGIN_WINDOW_SECONDS
    with _attempts_lock:
        recent = [t for t in _failed_attempts[key] if t > cutoff]
        _failed_attempts[key] = recent
        if len(recent) >= LOGIN_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed sign-in attempts. Try again later.",
            )


def _record_failure(key: str) -> None:
    with _attempts_lock:
        _failed_attempts[key].append(time.monotonic())


def _clear_failures(key: str) -> None:
    with _attempts_lock:
        _failed_attempts.pop(key, None)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    throttle_key = _throttle_key(request, email)
    _check_login_throttle(throttle_key)

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        _record_failure(throttle_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        _record_failure(throttle_key)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    _clear_failures(throttle_key)

    if user.role == "client" and user.client_id:
        # Engagement telemetry must never cost a valid user their login, but the
        # failure still has to be visible in the logs.
        try:
            db.add(models.EngagementEvent(client_id=user.client_id, event_type="LOGIN"))
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.warning("Could not record LOGIN engagement event for user %s", user.id, exc_info=True)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return schemas.TokenResponse(
        access_token=token, role=user.role, name=user.name,
        user_id=user.id, client_id=user.client_id,
    )


@router.get("/me", response_model=schemas.MeResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
