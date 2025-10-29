from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

try:  # pragma: no cover - optional dependency
    from celery import Celery
except Exception:  # pragma: no cover
    Celery = None  # type: ignore

from ..asr.engine import ASREngine, TranscriptionOptions, load_engine
from ..asr.types import Segment
from ..core.config import get_settings
from ..core.logging import logger
from ..db.models import JobStatus, TranscriptionJob, TranscriptArtifact, TranscriptSegment
from ..db.session import get_session

settings = get_settings()

if Celery:
    celery_app = Celery(
        "transcribe",
        broker=settings.broker_url,
        backend=settings.backend_url,
    )
    celery_app.conf.update(task_always_eager=os.getenv("CELERY_EAGER", "1") == "1")
else:  # pragma: no cover - fallback for environments without Celery
    celery_app = None

_engine: ASREngine | None = None


def get_engine() -> ASREngine:
    global _engine
    if _engine is None:
        _engine = load_engine()
    return _engine


def enqueue_transcription(job_id: str) -> None:
    if celery_app:
        if celery_app.conf.task_always_eager:
            process_transcription(job_id)
        else:
            celery_app.send_task("backend.workers.tasks.process_transcription", args=[job_id])
    else:
        process_transcription(job_id)


if celery_app:

    @celery_app.task(name="backend.workers.tasks.process_transcription")
    def process_transcription_task(job_id: str) -> None:  # pragma: no cover - executed via Celery
        process_transcription(job_id)


def process_transcription(job_id: str) -> None:
    logger.info("Starting transcription job %s", job_id)
    engine = get_engine()
    with get_session() as session:
        job = session.get(TranscriptionJob, job_id)
        if not job:
            logger.error("Job %s not found", job_id)
            return
        job.status = JobStatus.processing
        session.flush()

        options_dict = job.options or {}
        audio_path = Path(options_dict.get("audio_path"))
        transcription_options = _options_from_payload(options_dict)

        try:
            result = engine.transcribe(audio_path, transcription_options)
        except Exception as exc:  # pragma: no cover - safety
            job.status = JobStatus.failed
            job.error = str(exc)
            logger.exception("Job %s failed", job_id)
            return

        _store_result(session, job, result, audio_path)
        job.status = JobStatus.finished
        session.flush()
        logger.info("Finished transcription job %s", job_id)


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


def _store_result(session, job: TranscriptionJob, result, audio_path: Path) -> None:
    job.segments[:] = []
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

    output_dir = Path(settings.storage_dir) / job.id
    output_dir.mkdir(parents=True, exist_ok=True)

    text_path = output_dir / "transcript.txt"
    text_path.write_text(result.text, encoding="utf-8")
    _register_artifact(session, job, "txt", text_path)

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
    _register_artifact(session, job, "jsonl", jsonl_path)

    srt_path = output_dir / "transcript.srt"
    srt_path.write_text(_to_srt(result.segments), encoding="utf-8")
    _register_artifact(session, job, "srt", srt_path)

    vtt_path = output_dir / "transcript.vtt"
    vtt_path.write_text(_to_vtt(result.segments), encoding="utf-8")
    _register_artifact(session, job, "vtt", vtt_path)

    job.options.update(
        {
            "text": result.text,
            "dialect_text": result.dialect_mapped_text,
            "metadata": result.metadata,
            "audio_path": str(audio_path),
        }
    )


def _register_artifact(session, job: TranscriptionJob, format: str, path: Path) -> None:
    artifact = next((a for a in job.artifacts if a.format == format), None)
    if artifact:
        artifact.path = str(path)
    else:
        job.artifacts.append(TranscriptArtifact(format=format, path=str(path)))
    session.flush()


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
