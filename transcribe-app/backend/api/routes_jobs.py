from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..db.models import JobStatus, TranscriptionJob, TranscriptSegment
from ..db.schema import JobResultResponse, JobStatusResponse, SegmentSchema
from ..db.session import InMemorySession, get_db

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


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str, session: InMemorySession = Depends(get_db)
) -> JobStatusResponse:
    job = session.get(TranscriptionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    progress = 1.0 if job.status == JobStatus.finished else 0.0
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=progress,
        eta_seconds=None,
        error=job.error,
    )


@router.get("/jobs/{job_id}/result")
def download_job_result(
    job_id: str,
    format: str = "txt",
    session: InMemorySession = Depends(get_db),
):
    job = session.get(TranscriptionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
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
    job_id: str, session: InMemorySession = Depends(get_db)
) -> JobResultResponse:
    job = session.get(TranscriptionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.finished:
        raise HTTPException(status_code=400, detail="Job not finished yet")
    segments = _serialize_segments(job.segments)
    metadata = job.options or {}
    dialect_text = metadata.get("dialect_text")
    return JobResultResponse(
        job_id=job.id,
        status=job.status,
        text=metadata.get("text", ""),
        segments=segments,
        dialect_mapped_text=dialect_text,
        metadata=metadata,
    )
