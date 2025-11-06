# backend/api/main.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes_health import router as health_router
from .routes_transcribe import router as transcribe_router
from .routes_jobs import router as jobs_router

def create_app() -> FastAPI:
    # Trigger settings validation early (useful for detecting missing env vars)
    from ..core.config import get_settings

    get_settings()
    app = FastAPI(title="DialectTranscribe API", version="1.0.0")
    # CORS (adjust as needed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Mount routers under /api
    app.include_router(health_router, prefix="/api")
    app.include_router(transcribe_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    return app

app = create_app()
