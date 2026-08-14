"""
Database configuration.

Uses SQLite by default for zero-config local/demo use. Swap DATABASE_URL for
a Postgres/MySQL DSN in production — SQLAlchemy handles the rest.
"""

import logging
import os

from fastapi import HTTPException, status
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker, declarative_base

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "sqlite:///./dv_platform.db"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        """SQLite ignores foreign keys unless asked, which hides bad references."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def commit_session(db: Session, *, conflict_detail: str = "Request conflicts with existing data") -> None:
    """Commit, translating database failures into explicit HTTP responses.

    A bare commit surfaces constraint violations as an opaque 500 and leaves the
    session in a failed state for whatever runs next in the same request.
    """
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Commit rejected by a database constraint: %s", exc.orig)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_detail) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Commit failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is unavailable — please retry.",
        ) from exc
