from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from ..db.models import JobStatus


class JobFiles(BaseModel):
    txt: Optional[str] = None
    srt: Optional[str] = None
    vtt: Optional[str] = None
    jsonl: Optional[str] = None


class JobSummary(BaseModel):
    id: str
    status: JobStatus


class JobUploadResponse(BaseModel):
    id: str
    job_id: str
    status: JobStatus


class JobDetailResponse(BaseModel):
    id: str
    status: JobStatus
    text: Optional[str] = None
    dialect_text: Optional[str] = None
    error_message: Optional[str] = None
    original_filename: Optional[str] = None
    files: JobFiles
