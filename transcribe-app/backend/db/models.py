from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


Base = declarative_base()


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    finished = "finished"
    error = "error"


class TranscriptionJob(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status"), nullable=False, default=JobStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False, default="small")
    dialect_mapping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    input_path: Mapped[str] = mapped_column(Text, nullable=False)
    output_txt_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_srt_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_vtt_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_jsonl_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dialect_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


__all__ = ["Base", "TranscriptionJob", "JobStatus", "GUID"]
