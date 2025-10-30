from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from .models import JobStatus


def _to_dict(obj):
    return asdict(obj)


@dataclass
class SegmentSchema:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    confidence: float = 0.0
    language: Optional[str] = None

    def dict(self) -> Dict:
        return _to_dict(self)


@dataclass
class JobCreateResponse:
    job_id: str

    def dict(self) -> Dict:
        return _to_dict(self)


@dataclass
class UploadResponse:
    job_id: str

    def dict(self) -> Dict:
        return _to_dict(self)


@dataclass
class JobStatusResponse:
    job_id: str
    status: JobStatus
    progress: float = 0.0
    eta_seconds: Optional[int] = None
    error: Optional[str] = None

    def dict(self) -> Dict:
        return _to_dict(self)


@dataclass
class JobResultResponse:
    job_id: str
    status: JobStatus
    text: str
    segments: List[SegmentSchema]
    dialect_mapped_text: Optional[str]
    metadata: Dict

    def dict(self) -> Dict:
        data = _to_dict(self)
        data["segments"] = [segment.dict() for segment in self.segments]
        return data
