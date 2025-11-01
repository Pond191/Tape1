from __future__ import annotations

from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db.models import JobStatus, TranscriptionJob, TranscriptSegment
from ..db.schema import JobResultResponse, JobStatusResponse, SegmentSchema
from ..db.session import get_db

router = APIRouter()


def _serialize_segments(segments: list[TranscriptSegment]) -> list[SegmentSchema]:
    return [
        SegmentSchema(
            start=segment.start,
            end=segment.end,
            text=segment.text,
            speaker=segment.speaker,
            confidence=segment.confidence or 0.0,
            language=segment.language,
        )
        for segment in segments
    ]


def _get_job(session: Session, job_id: str) -> TranscriptionJob:
    try:
        job_uuid = uuid.UUID(str(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    job = session.get(TranscriptionJob, job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, session: Session = Depends(get_db)) -> JobStatusResponse:
    job = _get_job(session, job_id)
    progress = 1.0 if job.status == JobStatus.finished else 0.0
    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        progress=progress,
        eta_seconds=None,
        error=job.error,
        text=job.text,
        output_txt_path=job.output_txt_path,
        output_srt_path=job.output_srt_path,
        output_vtt_path=job.output_vtt_path,
        output_jsonl_path=job.output_jsonl_path,
    )


@router.get("/jobs/{job_id}/result")
def download_job_result(
    job_id: str,
    format: str = "txt",
    session: Session = Depends(get_db),
):
    job = _get_job(session, job_id)
    if job.status != JobStatus.finished:
        raise HTTPException(status_code=400, detail="Job not finished yet")

    path_map = {
        "txt": job.output_txt_path,
        "srt": job.output_srt_path,
        "vtt": job.output_vtt_path,
        "jsonl": job.output_jsonl_path,
    }
    selected = path_map.get(format)
    if not selected:
        artifact = next((a for a in job.artifacts if a.format == format), None)
        if artifact:
            selected = artifact.path
    if not selected:
        raise HTTPException(status_code=404, detail="Format not available")
    path = Path(selected)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact missing")
    media_types = {
        "txt": "text/plain",
        "srt": "application/x-subrip",
        "vtt": "text/vtt",
        "jsonl": "application/json",
    }
    filename = f"{job_id}.{format}"
    return _build_file_response(path, media_types.get(format, "application/octet-stream"), filename)


def _build_file_response(path: Path, media_type: str, filename: str) -> FileResponse:
    try:
        return FileResponse(path, media_type=media_type, filename=filename)
    except TypeError:  # pragma: no cover - compatibility with lightweight stubs
        return FileResponse(path)


def _serve_file(path_value: str | None, not_found_message: str, media_type: str, filename: str) -> FileResponse:
    if not path_value:
        raise HTTPException(status_code=404, detail=not_found_message)
    path = Path(path_value)
    if not path.exists():
        raise HTTPException(status_code=404, detail=not_found_message)
    return _build_file_response(path, media_type, filename)


@router.get("/jobs/{job_id}/txt")
def get_txt(job_id: str, session: Session = Depends(get_db)) -> FileResponse:
    job = _get_job(session, job_id)
    return _serve_file(
        job.output_txt_path,
        "TXT not found",
        "text/plain",
        f"{job_id}.txt",
    )


@router.get("/jobs/{job_id}/srt")
def get_srt(job_id: str, session: Session = Depends(get_db)) -> FileResponse:
    job = _get_job(session, job_id)
    return _serve_file(
        job.output_srt_path,
        "SRT not found",
        "application/x-subrip",
        f"{job_id}.srt",
    )


@router.get("/jobs/{job_id}/vtt")
def get_vtt(job_id: str, session: Session = Depends(get_db)) -> FileResponse:
    job = _get_job(session, job_id)
    return _serve_file(
        job.output_vtt_path,
        "VTT not found",
        "text/vtt",
        f"{job_id}.vtt",
    )


@router.get("/jobs/{job_id}/jsonl")
def get_jsonl(job_id: str, session: Session = Depends(get_db)) -> FileResponse:
    job = _get_job(session, job_id)
    return _serve_file(
        job.output_jsonl_path,
        "JSONL not found",
        "application/json",
        f"{job_id}.jsonl",
    )


@router.get("/jobs/{job_id}/result/inline", response_model=JobResultResponse)
def inline_job_result(
    job_id: str, session: Session = Depends(get_db)
) -> JobResultResponse:
    job = _get_job(session, job_id)
    if job.status != JobStatus.finished:
        raise HTTPException(status_code=400, detail="Job not finished yet")
    segments = _serialize_segments(job.segments)
    metadata = job.options or {}
    dialect_text = metadata.get("dialect_text")
    text = job.text or metadata.get("text", "")
    return JobResultResponse(
        job_id=str(job.id),
        status=job.status,
        text=text,
        segments=segments,
        dialect_mapped_text=dialect_text,
        metadata=metadata,
    )
