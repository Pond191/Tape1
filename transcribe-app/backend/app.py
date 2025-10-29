from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_health import router as health_router
from .api.routes_jobs import router as jobs_router
from .api.routes_transcribe import router as transcribe_router
from .core.config import get_settings
from .core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)


app.include_router(health_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(transcribe_router, prefix="/api")
