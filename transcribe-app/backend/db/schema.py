from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .models import JobStatus


class JobFiles(BaseModel):
    txt: Optional[str] = None
    srt: Optional[str] = None
    vtt: Optional[str] = None
    jsonl: Optional[str] = None

    class Config:
        orm_mode = True


class JobSummary(BaseModel):
    id: UUID
    status: JobStatus

    class Config:
        orm_mode = True


class JobUploadResponse(JobSummary):
    job_id: UUID


class JobDetailResponse(JobSummary):
    text: Optional[str] = None
    dialect_text: Optional[str] = None
    error_message: Optional[str] = None
    original_filename: Optional[str] = None
    files: JobFiles = Field(default_factory=JobFiles)

    class Config:
        orm_mode = True


__all__ = [
    "JobDetailResponse",
    "JobFiles",
    "JobSummary",
    "JobUploadResponse",
]
