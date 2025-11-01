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

    artifact = next((a for a in job.artifacts if a.format == format), None)
    if not artifact:
        raise HTTPException(status_code=404, detail="Format not available")
    path = Path(artifact.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact missing")
    return FileResponse(path)


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
    return JobResultResponse(
        job_id=str(job.id),
        status=job.status,
        text=metadata.get("text", ""),
        segments=segments,
        dialect_mapped_text=dialect_text,
        metadata=metadata,
    )
