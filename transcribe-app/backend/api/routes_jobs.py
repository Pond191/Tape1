from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.logging import logger
from ..db.models import TranscriptionJob
from ..db.schema import JobDetailResponse, JobFiles
from ..db.session import get_db

router = APIRouter()


def _get_job(session: Session, job_id: str) -> TranscriptionJob:
    try:
        job_uuid = uuid.UUID(str(job_id))
    except ValueError as exc:  # pragma: no cover - validation
        raise HTTPException(status_code=404, detail={"message": "งานไม่พบ"}) from exc

    job = session.get(TranscriptionJob, job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail={"message": "งานไม่พบ"})
    return job


def _build_files(job: TranscriptionJob) -> JobFiles:
    job_id = str(job.id)
    return JobFiles(
        txt=f"/api/jobs/{job_id}/txt" if job.output_txt_path else None,
        srt=f"/api/jobs/{job_id}/srt" if job.output_srt_path else None,
        vtt=f"/api/jobs/{job_id}/vtt" if job.output_vtt_path else None,
        jsonl=f"/api/jobs/{job_id}/jsonl" if job.output_jsonl_path else None,
    )


def _build_file_response(path: Path, media_type: str, filename: str) -> FileResponse:
    try:
        return FileResponse(path, media_type=media_type, filename=filename)
    except TypeError:  # pragma: no cover - compatibility for stubbed responses
        return FileResponse(path)


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, session: Session = Depends(get_db)) -> JobDetailResponse:
    job = _get_job(session, job_id)
    text_value = job.text
    if (not text_value or not text_value.strip()) and job.output_txt_path:
        try:
            text_path = Path(job.output_txt_path)
            if text_path.exists():
                text_value = text_path.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - defensive logging
            logger.warning("Unable to read transcript for job %s: %s", job_id, exc)

    return JobDetailResponse(
        id=job.id,
        status=job.status,
        text=text_value,
        dialect_text=job.dialect_text,
        error_message=job.error_message,
        original_filename=job.original_filename,
        files=_build_files(job),
    )


def _serve_artifact(path_value: str | None, media_type: str, filename: str) -> FileResponse:
    if not path_value:
        raise HTTPException(status_code=404, detail={"message": "ไฟล์ไม่พบ"})
    path = Path(path_value)
    if not path.exists():
        logger.error("Artifact %s missing on disk", path)
        raise HTTPException(status_code=404, detail={"message": "ไฟล์ไม่พบ"})
    return _build_file_response(path, media_type, filename)


@router.get("/jobs/{job_id}/txt")
def download_txt(job_id: str, session: Session = Depends(get_db)) -> FileResponse:
    job = _get_job(session, job_id)
    return _serve_artifact(
        job.output_txt_path,
        "text/plain",
        f"{job_id}.txt",
    )


@router.get("/jobs/{job_id}/srt")
def download_srt(job_id: str, session: Session = Depends(get_db)) -> FileResponse:
    job = _get_job(session, job_id)
    return _serve_artifact(
        job.output_srt_path,
        "application/x-subrip",
        f"{job_id}.srt",
    )


@router.get("/jobs/{job_id}/vtt")
def download_vtt(job_id: str, session: Session = Depends(get_db)) -> FileResponse:
    job = _get_job(session, job_id)
    return _serve_artifact(
        job.output_vtt_path,
        "text/vtt",
        f"{job_id}.vtt",
    )


@router.get("/jobs/{job_id}/jsonl")
def download_jsonl(job_id: str, session: Session = Depends(get_db)) -> FileResponse:
    job = _get_job(session, job_id)
    return _serve_artifact(
        job.output_jsonl_path,
        "application/json",
        f"{job_id}.jsonl",
    )
