from __future__ import annotations

from contextlib import contextmanager
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import get_settings
from .models import Base

logger = logging.getLogger(__name__)

_settings = get_settings()

_connect_args: dict[str, object] = {}
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


def _run_migrations() -> bool:
    config_candidates: list[Path] = []
    env_config = os.getenv("ALEMBIC_CONFIG")
    if env_config:
        config_candidates.append(Path(env_config))

    current_dir = Path(__file__).resolve()
    config_candidates.extend(
        [
            current_dir.parents[2] / "alembic.ini",  # backend/alembic.ini
            current_dir.parents[3] / "alembic.ini",  # project root
        ]
    )

    seen: set[Path] = set()
    for candidate in config_candidates:
        if not candidate:
            continue
        candidate = candidate.resolve()
        if candidate in seen or not candidate.exists():
            continue
        seen.add(candidate)
        try:
            from alembic import command  # type: ignore
            from alembic.config import Config  # type: ignore
        except Exception:  # pragma: no cover - alembic not installed
            logger.debug("Alembic not available; skipping migrations")
            return False

        logger.info("Running Alembic migrations using %s", candidate)
        config = Config(str(candidate))
        if not config.get_main_option("script_location"):
            script_location = candidate.parent / "alembic"
            if script_location.exists():
                config.set_main_option("script_location", str(script_location))
        command.upgrade(config, "head")
        return True
    return False


def init_db() -> None:
    if _run_migrations():
        return
    logger.info("Creating database tables via SQLAlchemy metadata")
    Base.metadata.create_all(bind=engine)


def _create_session() -> Session:
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    session = _create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
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
