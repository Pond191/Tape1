from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Generator, Iterator

from .models import TranscriptionJob

_DATABASE: Dict[str, TranscriptionJob] = {}


class InMemorySession:
    def add(self, job: TranscriptionJob) -> None:
        _DATABASE[job.id] = job

    def get(self, model, key):
        if model is TranscriptionJob:
            return _DATABASE.get(key)
        raise KeyError(f"Unsupported model {model}")

    def commit(self) -> None:  # pragma: no cover - compatibility hook
        pass

    def flush(self) -> None:  # pragma: no cover - compatibility hook
        pass

    def close(self) -> None:  # pragma: no cover - compatibility hook
        pass


def _create_session() -> InMemorySession:
    return InMemorySession()


def get_db() -> Generator[InMemorySession, None, None]:
    session = _create_session()
    try:
        yield session
    finally:
        session.close()


def get_session() -> Generator[InMemorySession, None, None]:
    yield from get_db()


@contextmanager
def db_session() -> Iterator[InMemorySession]:
    session = _create_session()
    try:
        yield session
    finally:
        session.close()
