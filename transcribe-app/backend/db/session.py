from __future__ import annotations

from contextlib import contextmanager
import logging
import os
from pathlib import Path
from typing import Generator, Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import get_settings
from .models import Base

logger = logging.getLogger(__name__)

_ENGINE: Optional[Engine] = None
_SESSION_FACTORY: Optional[sessionmaker] = None


def _ensure_engine() -> Engine:
    global _ENGINE, _SESSION_FACTORY

    settings = get_settings()
    if _ENGINE is not None and str(_ENGINE.url) == settings.database_url:
        return _ENGINE

    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    logger.info("Connecting to database %s", settings.database_url)
    _ENGINE = create_engine(
        settings.database_url,
        future=True,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    _SESSION_FACTORY = sessionmaker(
        bind=_ENGINE,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    return _ENGINE


def get_engine() -> Engine:
    return _ensure_engine()


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
    engine = _ensure_engine()
    if _run_migrations():
        return
    logger.info("Creating database tables via SQLAlchemy metadata")
    Base.metadata.create_all(bind=engine)


def _create_session() -> Session:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _ensure_engine()
    assert _SESSION_FACTORY is not None  # for type checkers
    return _SESSION_FACTORY()


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
