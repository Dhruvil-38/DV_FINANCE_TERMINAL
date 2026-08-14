"""
Authentication & authorization.

- Passwords hashed with bcrypt (passlib).
- Stateless auth via short-lived JWT access tokens (python-jose).
- Role-based guards: require_role(...) as a FastAPI dependency.

The signing secret is read from DV_JWT_SECRET and never falls back to a
checked-in default — an unset secret raises at import time so a deployment
cannot silently run with forgeable tokens. For local development, set
DV_ALLOW_EPHEMERAL_JWT_SECRET=1 to generate a random per-process secret
(tokens then stop working across restarts, which is the intended signal).
"""

import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Iterable

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
import models

logger = logging.getLogger(__name__)

MIN_SECRET_LENGTH = 32


def _load_secret_key() -> str:
    secret = os.environ.get("DV_JWT_SECRET", "").strip()
    if secret:
        if len(secret) < MIN_SECRET_LENGTH:
            raise RuntimeError(
                f"DV_JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters long."
            )
        return secret
    if os.environ.get("DV_ALLOW_EPHEMERAL_JWT_SECRET", "").lower() in ("1", "true", "yes"):
        return secrets.token_urlsafe(48)
    raise RuntimeError(
        "DV_JWT_SECRET is not set. Generate one with "
        "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"` and export it, "
        "or set DV_ALLOW_EPHEMERAL_JWT_SECRET=1 for a throwaway local run."
    )


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # A stored hash that bcrypt cannot parse is a data problem, not a 500.
        logger.error("Stored password hash is not a valid bcrypt hash", exc_info=True)
        return False


def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        logger.info("Rejected token: %s", exc)
        raise credentials_exception from exc

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Token carries an unusable 'sub' claim: %r", payload.get("sub"))
        raise credentials_exception from exc

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*allowed_roles: Iterable[str]):
    """Usage: Depends(require_role('admin', 'analyst'))"""

    def _guard(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted to access this resource",
            )
        return user

    return _guard


FIRM_ROLES = ("admin", "analyst", "staff")
