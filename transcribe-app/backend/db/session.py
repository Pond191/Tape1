from __future__ import annotations

from contextlib import contextmanager
from typing import Dict

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


@contextmanager
def get_session():
    session = InMemorySession()
    try:
        yield session
    finally:
        session.close()
