from __future__ import annotations

import asyncio
import mimetypes
import shutil
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.logging import logger
from ..db.models import JobStatus, TranscriptionJob
from ..db.schema import JobUploadResponse
from ..db.session import get_db
from ..workers.tasks import enqueue_transcription

router = APIRouter()
settings = get_settings()

mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/mp4", ".m4a")
mimetypes.add_type("audio/x-m4a", ".m4a")

_CHUNK_SIZE = 1024 * 1024
_ALLOWED_MODELS = {"small", "medium", "large-v3"}


def _sanitize_filename(name: str) -> str:
    base = Path(name or "").name
    normalized = unicodedata.normalize("NFC", base)
    allowed: list[str] = []
    for char in normalized:
        if char in {"/", "\\", "\x00"}:
            continue
        if char.isprintable():
            allowed.append(char)
    sanitized = "".join(allowed).strip()
    if not sanitized:
        return "audio"
    if sanitized.startswith("."):
        sanitized = sanitized.lstrip(".") or "audio"
    return sanitized[:255]


def _resolve_extension(filename: str, content_type: str | None) -> str:
    suffix = Path(filename).suffix
    if suffix:
        return suffix
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    return ".bin"


async def _read_chunk(upload: UploadFile, size: int) -> bytes:
    reader = getattr(upload, "read", None)
    if reader is None:
        stream = getattr(upload, "file", None)
        if stream is None:
            return b""
        return stream.read(size)
    try:
        maybe_chunk = reader(size)
    except TypeError:
        maybe_chunk = reader()
    if asyncio.iscoroutine(maybe_chunk):
        return await maybe_chunk
    return maybe_chunk or b""


async def _close_upload(upload: UploadFile) -> None:
    closer = getattr(upload, "close", None)
    if closer is None:
        stream = getattr(upload, "file", None)
        if stream is not None and hasattr(stream, "close"):
            stream.close()
        return
    result = closer()
    if asyncio.iscoroutine(result):
        await result


async def _persist_upload(destination: Path, upload: UploadFile) -> int:
    max_bytes = settings.max_upload_mb * 1024 * 1024
    total = 0
    try:
        with destination.open("wb") as outfile:
            while True:
                chunk = await _read_chunk(upload, _CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "message": f"ไฟล์มีขนาดใหญ่เกินกำหนด (สูงสุด {settings.max_upload_mb} MB)",
                        },
                    )
                outfile.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:  # pragma: no cover - defensive cleanup
        destination.unlink(missing_ok=True)
        logger.exception("Failed writing upload %s: %s", destination, exc)
        raise HTTPException(status_code=500, detail={"message": "ไม่สามารถบันทึกไฟล์ได้"}) from exc
    finally:
        await _close_upload(upload)

    if total == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail={"message": "ไม่พบข้อมูลในไฟล์ที่อัปโหลด"})
    return total


def _get_source_path(upload: UploadFile) -> Path | None:
    file_obj = getattr(upload, "file", None)
    name = getattr(file_obj, "name", None)
    if isinstance(name, str) and name:
        path = Path(name)
        if path.exists():
            return path
    return None


def _copy_sidecar(source_path: Path | None, destination: Path) -> None:
    if not source_path:
        return
    sidecar = source_path.with_suffix(".json")
    if not sidecar.exists():
        return
    try:
        shutil.copy(sidecar, destination.with_suffix(".json"))
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Failed to copy sidecar %s: %s", sidecar, exc)


def _normalize_model(model_size: str | None) -> str:
    model = (model_size or settings.default_model_size or "small").strip().lower()
    if model not in _ALLOWED_MODELS:
        logger.warning("Model %s not allowed; falling back to small", model)
        return "small"
    return model


def _coerce_bool(value: bool | str | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


@router.post("/upload", response_model=JobUploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    model_size: str = Form("small"),
    enable_dialect_map: bool | str | None = Form(False),
    session: Session = Depends(get_db),
) -> JobUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail={"message": "กรุณาเลือกไฟล์เสียง"})

    content_type = getattr(file, "content_type", "") or ""
    detected_type = content_type or mimetypes.guess_type(file.filename or "")[0]
    if detected_type and not detected_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail={"message": "ชนิดไฟล์ไม่รองรับ"})

    job_uuid = uuid.uuid4()
    job_id = str(job_uuid)
    upload_day = datetime.utcnow().strftime("%Y%m%d")
    upload_dir = Path(settings.storage_dir) / "uploads" / upload_day
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_name = _sanitize_filename(file.filename)
    extension = _resolve_extension(original_name, content_type)
    destination = upload_dir / f"{job_id}{extension}"

    source_path = _get_source_path(file)
    size = await _persist_upload(destination, file)
    _copy_sidecar(source_path, destination)

    job = TranscriptionJob(
        id=job_uuid,
        status=JobStatus.pending,
        original_filename=original_name,
        model_name=_normalize_model(model_size),
        dialect_mapping=_coerce_bool(enable_dialect_map),
        input_path=str(destination),
    )

    session.add(job)
    session.commit()
    session.refresh(job)

    try:
        enqueue_transcription(str(job.id))
    except Exception as exc:
        logger.exception("Failed to enqueue job %s: %s", job_id, exc)
        job.status = JobStatus.error
        job.error_message = "ไม่สามารถคิวงานได้"
        session.commit()
        raise HTTPException(status_code=500, detail={"message": "ไม่สามารถสร้างงานได้"}) from exc

    logger.info(
        "Created transcription job %s for %s (%s bytes)",
        job_id,
        original_name,
        size,
    )
    return JobUploadResponse(id=job.id, job_id=job.id, status=job.status)


@router.post("/transcribe", response_model=JobUploadResponse)
async def create_transcription_job(
    file: UploadFile = File(...),
    model_size: str = Form("small"),
    enable_dialect_map: bool | str | None = Form(False),
    session: Session = Depends(get_db),
) -> JobUploadResponse:
    """Alias endpoint that mirrors :func:`upload_audio` for backward compatibility."""

    return await upload_audio(
        file=file,
        model_size=model_size,
        enable_dialect_map=enable_dialect_map,
        session=session,
    )
