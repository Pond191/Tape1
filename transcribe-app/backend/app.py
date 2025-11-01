from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

try:
    from fastapi.exceptions import RequestValidationError
except ImportError:  # pragma: no cover - fallback for minimal fastapi stubs
    class RequestValidationError(Exception):  # type: ignore[override]
        def __init__(self, errors=None) -> None:
            super().__init__("Validation error")
            self._errors = errors or []

        def errors(self):  # type: ignore[override]
            return self._errors

from .api.routes_health import router as health_router
from .api.routes_jobs import router as jobs_router
from .api.routes_transcribe import router as transcribe_router
from .core.config import get_settings
from .core.logging import configure_logging, logger
from .db.session import init_db

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
    init_db()

    base_dir = Path(settings.storage_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir = base_dir / "uploads"
    jobs_dir = base_dir / "jobs"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    jobs_dir.mkdir(parents=True, exist_ok=True)

    if os.geteuid() == 0:
        try:
            import grp
            import pwd

            app_user = pwd.getpwnam("app")
            app_group = grp.getgrnam("app")
            for path in (base_dir, uploads_dir, jobs_dir):
                os.chown(path, app_user.pw_uid, app_group.gr_gid)
        except KeyError:
            logger.warning("User or group 'app' not found; skipping chown for %s", base_dir)
        except PermissionError:
            logger.warning("Insufficient permission to chown %s", base_dir)
    elif not os.access(base_dir, os.W_OK):
        logger.warning("Storage directory %s is not writable", base_dir)


app.include_router(health_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(transcribe_router, prefix="/api")


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        content: dict[str, Any] = detail
    else:
        message = str(detail) if detail else "เกิดข้อผิดพลาด"
        content = {"message": message}
    return JSONResponse(status_code=exc.status_code, content=content)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "message": "ข้อมูลที่ส่งมาไม่ถูกต้อง",
            "errors": exc.errors(),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    message = str(exc) or "เกิดข้อผิดพลาดภายในระบบ"
    return JSONResponse(status_code=500, content={"message": message})


if hasattr(app, "add_exception_handler"):
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
else:  # pragma: no cover - fallback for lightweight FastAPI stubs
    logger.warning("Custom exception handlers are not supported by this FastAPI build")
