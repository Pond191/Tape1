"""FastAPI application entrypoint used by Uvicorn.

This wraps the existing backend.app FastAPI instance so that the
entrypoint script can reference ``app.main:app`` without duplicating
configuration.
"""

from backend.app import app

__all__ = ["app"]
