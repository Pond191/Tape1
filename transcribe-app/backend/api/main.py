from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.logging import logger
from ..db.session import init_db
from .routes_health import router as health_router
from .routes_jobs import router as jobs_router
from .routes_transcribe import router as transcribe_router

app = FastAPI(title="DialectTranscribe API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ปรับตามที่ใช้จริง
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(transcribe_router, prefix="/api", tags=["transcribe"])
app.include_router(jobs_router, prefix="/api", tags=["jobs"])


@app.on_event("startup")
def _startup():
    try:
        init_db()
        logger.info("DB initialized")
    except Exception as exc:
        logger.exception("DB init failed: %s", exc)
