from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import structlog
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = structlog.get_logger(__name__)

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        from app.core.config import get_settings
        settings = get_settings()
        is_sqlite = settings.database_url.startswith("sqlite")
        connect_args = {"check_same_thread": False} if is_sqlite else {}
        engine = create_engine(
            settings.database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            **({"pool_size": 5, "max_overflow": 10, "pool_timeout": 30} if not is_sqlite else {}),
            echo=settings.debug,
        )
        if is_sqlite:
            # SQLite has no schema support; map recsys → default schema
            engine = engine.execution_options(schema_translate_map={"recsys": None})
        _engine = engine
    return _engine


def _get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


class Base(DeclarativeBase):
    metadata = MetaData(schema="recsys")


# Convenience alias used by tests that set up their own engine
def reset_engine(new_engine) -> None:
    """Reset the engine and session factory — used in tests."""
    global _engine, _SessionLocal
    _engine = new_engine
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)


def init_db() -> None:
    from app.db import models as _models  # noqa: F401 — registers ORM models with Base
    engine = _get_engine()
    if not str(engine.url).startswith("sqlite"):
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS recsys"))
    Base.metadata.create_all(bind=engine, checkfirst=True)
    from app.core.config import get_settings
    settings = get_settings()
    logger.info("database_initialized", url=settings.database_url.split("@")[-1])


def check_db_health() -> bool:
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("db_health_check_failed", error=str(exc))
        return False


@contextmanager
def get_db() -> Generator[Session, None, None]:
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_dep() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    with get_db() as session:
        yield session


# Backwards-compatible alias
SessionLocal = property(lambda self: _get_session_factory())


class _SessionLocalProxy:
    def __call__(self):
        return _get_session_factory()()

    def __enter__(self):
        self._s = _get_session_factory()()
        return self._s

    def __exit__(self, *args):
        self._s.close()


SessionLocal = _SessionLocalProxy()
