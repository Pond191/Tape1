from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency
    from celery import Celery, shared_task
except Exception:  # pragma: no cover
    Celery = None  # type: ignore

    def shared_task(*_args, **_kwargs):  # type: ignore
        def decorator(func):
            return func

        return decorator

from sqlalchemy.orm import Session

from ..asr.engine import ASREngine, TranscriptionOptions, load_engine
from ..asr.types import Segment
from ..core.config import get_settings
from ..core.logging import logger
from ..db.models import (
    JobStatus,
    TranscriptArtifact,
    TranscriptSegment,
    TranscriptionJob,
)
from ..db.session import db_session

settings = get_settings()

celery_app: Optional[Celery] = None
if Celery and os.getenv("CELERY_BROKER_URL"):
    celery_app = Celery(
        "transcribe",
        broker=os.getenv("CELERY_BROKER_URL"),
        backend=os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL")),
    )
    celery_app.conf.update(task_always_eager=os.getenv("CELERY_EAGER", "1") == "1")
    celery_app.set_default()

_QUEUE_NAME = os.getenv("CELERY_QUEUE", "transcribe")
_engine: ASREngine | None = None


def get_engine() -> ASREngine:
    global _engine
    if _engine is None:
        _engine = load_engine()
    return _engine


def enqueue_transcription(job_id: str) -> None:
    try:
        if celery_app:
            process_transcription.apply_async(args=[str(job_id)], queue=_QUEUE_NAME)
            return
    except Exception:
        logger.exception("Celery enqueue failed; falling back to local processing")

    try:
        _run_transcription(job_id)
    except Exception:
        logger.exception("Local transcription failed")


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=1,
    name="backend.workers.tasks.process_transcription",
)
def process_transcription(self, job_id: str) -> None:  # pragma: no cover - executed via Celery
    _run_transcription(job_id, task=self)


def _run_transcription(job_id: str, task=None) -> None:
    logger.info("Starting transcription job %s", job_id)
    try:
        job_uuid = uuid.UUID(str(job_id))
    except ValueError:
        logger.error("Invalid job id %s", job_id)
        return

    engine = get_engine()
    with db_session() as session:
        job = _load_job(session, job_uuid, task)
        if job is None:
            return

        job.status = JobStatus.processing
        job.error = None
        job.touch()
        session.commit()

        options_dict = dict(job.options or {})
        job.options = options_dict
        audio_path = Path(options_dict.get("audio_path", ""))
        transcription_options = _options_from_payload(options_dict)

        try:
            result = engine.transcribe(audio_path, transcription_options)
        except Exception as exc:  # pragma: no cover - safety
            job.status = JobStatus.failed
            job.error = str(exc)
            job.touch()
            session.commit()
            logger.exception("Job %s failed", job_id)
            return

        _store_result(session, job, result, audio_path)
        job.status = JobStatus.finished
        job.touch()
        session.commit()
        logger.info("Finished transcription job %s", job_id)


def _load_job(session: Session, job_uuid: uuid.UUID, task) -> Optional[TranscriptionJob]:
    job = session.get(TranscriptionJob, job_uuid)
    if job:
        return job

    if task is not None and hasattr(task, "retry"):
        try:
            raise task.retry()
        except task.MaxRetriesExceededError:  # type: ignore[attr-defined]
            logger.error("Job %s not found after retries", job_uuid)
            return None
    logger.error("Job %s not found", job_uuid)
    return None


def _options_from_payload(payload: Dict) -> TranscriptionOptions:
    return TranscriptionOptions(
        model_size=payload.get("model_size", settings.default_model_size),
        language_hint=payload.get("language_hint"),
        enable_diarization=payload.get("enable_diarization", True),
        enable_punct=payload.get("enable_punct", True),
        enable_itn=payload.get("enable_itn", True),
        enable_dialect_map=payload.get("enable_dialect_map", False),
        custom_lexicon=payload.get("custom_lexicon"),
        context_prompt=payload.get("context_prompt"),
    )


def _store_result(session: Session, job: TranscriptionJob, result, audio_path: Path) -> None:
    job.segments.clear()
    for segment in result.segments:
        job.segments.append(
            TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text,
                speaker=segment.speaker,
                confidence=segment.confidence,
                language=segment.language,
            )
        )

    output_dir = Path(settings.storage_dir) / str(job.id)
    output_dir.mkdir(parents=True, exist_ok=True)

    text_path = output_dir / "transcript.txt"
    text_path.write_text(result.text, encoding="utf-8")
    _register_artifact(job, "txt", text_path)

    jsonl_path = output_dir / "transcript.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as file:
        for segment in result.segments:
            payload = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": segment.confidence,
                "speaker": segment.speaker,
                "language": segment.language,
            }
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")
    _register_artifact(job, "jsonl", jsonl_path)

    srt_path = output_dir / "transcript.srt"
    srt_path.write_text(_to_srt(result.segments), encoding="utf-8")
    _register_artifact(job, "srt", srt_path)

    vtt_path = output_dir / "transcript.vtt"
    vtt_path.write_text(_to_vtt(result.segments), encoding="utf-8")
    _register_artifact(job, "vtt", vtt_path)

    job.options.update(
        {
            "text": result.text,
            "dialect_text": result.dialect_mapped_text,
            "metadata": result.metadata,
            "audio_path": str(audio_path),
        }
    )


def _register_artifact(job: TranscriptionJob, format: str, path: Path) -> None:
    artifact = next((a for a in job.artifacts if a.format == format), None)
    if artifact:
        artifact.path = str(path)
    else:
        job.artifacts.append(TranscriptArtifact(format=format, path=str(path)))


def _format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")


def _to_srt(segments: List[Segment]) -> str:
    lines = []
    for index, segment in enumerate(segments, start=1):
        start = _format_timestamp(segment.start)
        end = _format_timestamp(segment.end)
        speaker_prefix = f"{segment.speaker}: " if segment.speaker else ""
        lines.append(str(index))
        lines.append(f"{start} --> {end}")
        lines.append(f"{speaker_prefix}{segment.text}")
        lines.append("")
    return "\n".join(lines).strip()


def _to_vtt(segments: List[Segment]) -> str:
    lines = ["WEBVTT", ""]
    for segment in segments:
        start = _format_timestamp(segment.start).replace(",", ".")
        end = _format_timestamp(segment.end).replace(",", ".")
        speaker_prefix = f"{segment.speaker}: " if segment.speaker else ""
        lines.append(f"{start} --> {end}")
        lines.append(f"{speaker_prefix}{segment.text}")
        lines.append("")
    return "\n".join(lines).strip()
