from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from backend.db.models import JobStatus

class JobFiles(BaseModel):
    txt: Optional[str] = None
    srt: Optional[str] = None
    vtt: Optional[str] = None
    jsonl: Optional[str] = None

class JobUploadResponse(BaseModel):
    id: str
    job_id: str
    status: JobStatus

class JobDetailResponse(BaseModel):
    id: str
    status: JobStatus
    text: Optional[str]
    dialect_text: Optional[str]
    error_message: Optional[str]
    original_filename: Optional[str]
    files: JobFiles
