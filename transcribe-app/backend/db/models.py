from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    finished = "finished"
    failed = "failed"


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    confidence: float = 0.0
    language: Optional[str] = None


@dataclass
class TranscriptArtifact:
    format: str
    path: str


@dataclass
class TranscriptionJob:
    id: str
    filename: str
    status: JobStatus = JobStatus.pending
    model_size: str = "small"
    options: Dict = field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    segments: List[TranscriptSegment] = field(default_factory=list)
    artifacts: List[TranscriptArtifact] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
