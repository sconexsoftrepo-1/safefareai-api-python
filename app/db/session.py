"""SQL Server engine/session management (SQLAlchemy 2.x + pyodbc).

The schema is owned by the Flyway migrations of the Java BFF. This module never creates, alters or drops tables.
"""
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.exceptions import AppError, ConfigurationError, ConflictError, DatabaseError, DatabaseUnavailableError

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        if not settings.database_configured:
            raise ConfigurationError("Database connection is not configured")
        _engine = create_engine(
            settings.sqlalchemy_url(),
            pool_pre_ping=True,
            pool_size=settings.safefare_db_pool_size,
            max_overflow=settings.safefare_db_max_overflow,
            pool_recycle=1800,
            connect_args={"timeout": settings.safefare_db_login_timeout},
        )
        _session_factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed (uncommitted work is rolled back)."""
    get_engine()
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def transaction(db: Session) -> Iterator[Session]:
    """Commit on success, roll back on any failure. SQLAlchemy errors become sanitized DatabaseErrors."""
    try:
        yield db
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Integrity error, transaction rolled back: %s", type(exc.orig).__name__)
        raise ConflictError("The change conflicts with existing data; nothing was saved",
                            code="DATABASE_CONSTRAINT") from exc
    except OperationalError as exc:
        db.rollback()
        logger.error("Database unavailable, transaction rolled back")
        raise DatabaseUnavailableError() from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error, transaction rolled back")
        raise DatabaseError() from exc
    except AppError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def check_database() -> bool:
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT 1")).scalar() == 1


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
