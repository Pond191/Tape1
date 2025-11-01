from __future__ import annotations

import asyncio
import json
import mimetypes
import shutil
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.logging import logger
from ..db.models import TranscriptionJob
from ..db.schema import UploadResponse
from ..db.session import get_db
from ..workers.tasks import enqueue_transcription

router = APIRouter()
settings = get_settings()

mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/mp4", ".m4a")
mimetypes.add_type("audio/x-m4a", ".m4a")

_CHUNK_SIZE = 1024 * 1024


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


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


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
    if sidecar.exists():
        shutil.copy(sidecar, destination.with_suffix(".json"))


async def _create_job(
    *,
    session: Session,
    file: UploadFile,
    model_size: str,
    enable_dialect_map: bool,
    enable_diarization: bool,
    enable_punct: bool,
    enable_itn: bool,
    language_hint: str | None,
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail={"message": "กรุณาเลือกไฟล์เสียง"})

    model_size = str(model_size or settings.default_model_size)

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

    enable_dialect_map = _coerce_bool(enable_dialect_map)
    enable_diarization = _coerce_bool(enable_diarization)
    enable_punct = _coerce_bool(enable_punct)
    enable_itn = _coerce_bool(enable_itn)

    if isinstance(language_hint, str):
        language_hint = language_hint.strip() or None

    job_options: Dict[str, Any] = {
        "audio_path": str(destination),
        "model_size": model_size,
        "enable_dialect_map": enable_dialect_map,
        "enable_diarization": enable_diarization,
        "enable_punct": enable_punct,
        "enable_itn": enable_itn,
        "original_filename": original_name,
        "content_type": detected_type or content_type,
        "file_size": size,
    }
    if language_hint:
        job_options["language_hint"] = language_hint

    job = TranscriptionJob(
        id=job_uuid,
        filename=original_name,
        model_size=model_size,
        options=job_options,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    enqueue_transcription(str(job.id))
    logger.info(
        "Created transcription job %s for %s (%s bytes)",
        job_id,
        original_name,
        size,
    )

    return UploadResponse(job_id=str(job.id))


@router.post("/upload", response_model=UploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    model_size: str = Form(...),
    enable_dialect_map: bool = Form(False),
    enable_diarization: bool = Form(True),
    enable_punct: bool = Form(True),
    enable_itn: bool = Form(True),
    language_hint: str | None = Form(None),
    session: Session = Depends(get_db),
) -> UploadResponse:
    return await _create_job(
        session=session,
        file=file,
        model_size=model_size,
        enable_dialect_map=enable_dialect_map,
        enable_diarization=enable_diarization,
        enable_punct=enable_punct,
        enable_itn=enable_itn,
        language_hint=language_hint,
    )


@router.post("/transcribe", response_model=UploadResponse)
async def create_transcription_job(
    file: UploadFile = File(...),
    options: str = Form("{}"),
    session: Session = Depends(get_db),
) -> UploadResponse:
    try:
        payload: Dict[str, Any] = json.loads(options) if options else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail={"message": "Invalid options JSON"}) from exc

    return await _create_job(
        session=session,
        file=file,
        model_size=payload.get("model_size", settings.default_model_size),
        enable_dialect_map=payload.get("enable_dialect_map", False),
        enable_diarization=payload.get("enable_diarization", True),
        enable_punct=payload.get("enable_punct", True),
        enable_itn=payload.get("enable_itn", True),
        language_hint=payload.get("language_hint"),
    )
