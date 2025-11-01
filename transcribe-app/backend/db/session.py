from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import get_settings
from .models import Base

_settings = get_settings()

_connect_args = {}
if _settings.database_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    _settings.database_url,
    future=True,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def _create_session() -> Session:
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    session = _create_session()
    try:
        yield session
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    yield from get_db()


@contextmanager
def db_session() -> Iterator[Session]:
    session = _create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Backwards compatibility alias for existing imports
InMemorySession = Session
