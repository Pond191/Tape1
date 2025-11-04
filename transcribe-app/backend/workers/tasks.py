from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency
    from celery import shared_task
except Exception:  # pragma: no cover
    def shared_task(*_args, **_kwargs):  # type: ignore
        def decorator(func):
            return func
        return decorator

from sqlalchemy.exc import OperationalError

from ..asr.engine import ASREngine, TranscriptionOptions, load_engine
from ..asr.types import Segment
from ..core.config import get_settings
from ..core.logging import logger
from ..db.models import JobStatus, TranscriptionJob
from ..db.session import db_session, init_db
from .celery_app import QUEUE_NAME, celery_app

settings = get_settings()

# Ensure metadata is created even when the worker starts before the API
try:  # pragma: no cover - the DB may be unavailable during imports in tests
    init_db()
except Exception:
    logger.debug("Database not ready during worker import; will retry later")

_engine: Optional[ASREngine] = None


def get_engine() -> ASREngine:
    """Singleton loader for the ASR engine."""
    global _engine
    if _engine is None:
        _engine = load_engine()
    return _engine


def enqueue_transcription(job_id: str) -> None:
    """Enqueue a transcription job via Celery; fallback to sync if Celery unavailable."""
    if celery_app is not None:
        try:
            transcribe_audio.apply_async(args=[str(job_id)], queue=QUEUE_NAME)
            return
        except Exception as exc:
            logger.exception("Celery enqueue failed for job %s: %s", job_id, exc)
            raise

    logger.warning("Celery unavailable; running job %s synchronously", job_id)
    _run_transcription(job_id, task=None)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=1,
    name="backend.workers.tasks.transcribe_audio",
)
def transcribe_audio(self, job_id: str) -> None:  # pragma: no cover - executed via Celery
    _run_transcription(job_id, task=self)


def _run_transcription(job_id: str, task=None) -> None:
    logger.info("Starting transcription job %s", job_id)
    try:
        job_uuid = uuid.UUID(str(job_id))
    except ValueError:
        logger.error("Invalid job id %s", job_id)
        return

    job_payload = _acquire_job(job_uuid, task)
    if job_payload is None:
        return

    try:
        result_payload = _transcribe(job_uuid, job_payload)
    except FileNotFoundError as exc:
        logger.error("Input audio missing for job %s: %s", job_id, exc)
        _mark_job_error(job_uuid, str(exc))
        return
    except Exception as exc:  # pragma: no cover - safety
        logger.exception("Transcription failed for job %s", job_id)
        _mark_job_error(job_uuid, str(exc))
        return

    _mark_job_finished(job_uuid, result_payload)
    logger.info("Finished transcription job %s", job_id)


def _acquire_job(job_uuid: uuid.UUID, task) -> Optional[Dict[str, Any]]:
    """Load the job from DB and mark it running; retry a few times if DB is not ready."""
    with db_session() as session:
        try:
            job = session.get(TranscriptionJob, job_uuid)
        except OperationalError as exc:  # pragma: no cover - DB race
            session.rollback()
            logger.warning("Database not ready when fetching job %s: %s", job_uuid, exc)
            if task is not None and hasattr(task, "retry"):
                try:
                    raise task.retry(exc=exc)
                except task.MaxRetriesExceededError:  # type: ignore[attr-defined]
                    logger.error("Job %s not found after retries", job_uuid)
                    return None
            raise

        if job is None:
            if task is not None and hasattr(task, "retry"):
                try:
                    raise task.retry()
                except task.MaxRetriesExceededError:  # type: ignore[attr-defined]
                    logger.error("Job %s not found after retries", job_uuid)
                    return None
            logger.error("Job %s not found", job_uuid)
            return None

        job.status = JobStatus.running
        job.error_message = None
        job.touch()
        session.commit()

        return {
            "id": job.id,
            "input_path": job.input_path,
            "model_name": job.model_name or settings.default_model_size,
            "dialect_mapping": bool(job.dialect_mapping),
        }


def _transcribe(job_uuid: uuid.UUID, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Core transcription routine: prepare audio, call engine, write outputs."""
    input_path = Path(payload["input_path"]).expanduser()
    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    job_dir = Path(settings.storage_dir) / "jobs" / str(job_uuid)
    job_dir.mkdir(parents=True, exist_ok=True)

    prepared_audio = job_dir / "audio.wav"
    _convert_audio(input_path, prepared_audio)
    _copy_transcript_sidecar(input_path, prepared_audio)

    engine = get_engine()
    options = TranscriptionOptions(
        model_size=payload.get("model_name", settings.default_model_size),
        enable_dialect_map=payload.get("dialect_mapping", False),
    )
    result = engine.transcribe(prepared_audio, options)

    # --- Build plain text safely ---
    # ใช้ข้อความจาก segments เป็นหลัก; ถ้าไม่มีค่อยพิจารณา result.text
    segment_texts = [
        (segment.text or "").strip()
        for segment in getattr(result, "segments", []) or []
        if (getattr(segment, "text", "") or "").strip()
    ]
    joined = "\n".join(segment_texts).strip()
    candidate = (getattr(result, "text", "") or "").strip()

    # กันเคส placeholder สั้น ๆ เช่น "audio."
    if not joined:
        if candidate and len(candidate) >= 8 and candidate.lower() not in {"audio.", "audio", "file", "sound"}:
            plain_text = candidate
        else:
            plain_text = "(no speech detected or ASR backend returned no segments)"
    else:
        plain_text = joined

    # เขียนไฟล์ผลลัพธ์
    text_path = job_dir / "transcript.txt"
    text_path.write_text(plain_text, encoding="utf-8")
    logger.info("Wrote transcript.txt with %d characters", len(plain_text))

    jsonl_path = job_dir / "segments.jsonl"
    _write_segments(jsonl_path, getattr(result, "segments", []) or [])

    srt_path = job_dir / "transcript.srt"
    srt_path.write_text(_to_srt(getattr(result, "segments", []) or []), encoding="utf-8")
    logger.info("Wrote %s", srt_path)

    vtt_path = job_dir / "transcript.vtt"
    vtt_path.write_text(_to_vtt(getattr(result, "segments", []) or []), encoding="utf-8")
    logger.info("Wrote %s", vtt_path)

    return {
        "text": plain_text,
        "dialect_text": getattr(result, "dialect_mapped_text", None),
        "txt_path": str(text_path),
        "srt_path": str(srt_path),
        "vtt_path": str(vtt_path),
        "jsonl_path": str(jsonl_path),
    }


def _convert_audio(source: Path, destination: Path) -> None:
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        shutil.copy(source, destination)
        logger.warning("ffmpeg not available; copied %s to %s without conversion", source, destination)
        return

    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(source),
        "-ar", "16000",
        "-ac", "1",
        str(destination),
    ]
    logger.info("Converting %s to mono WAV via ffmpeg", source)
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {completed.stderr.strip()}")


def _copy_transcript_sidecar(source: Path, converted: Path) -> None:
    """If a sidecar JSON transcript exists beside the original, copy it next to converted audio."""
    sidecar = source.with_suffix(".json")
    if not sidecar.exists():
        return
    target = converted.with_suffix(".json")
    try:
        shutil.copy(sidecar, target)
        logger.info("Copied sidecar %s to %s", sidecar, target)
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Failed to copy sidecar %s: %s", sidecar, exc)


def _write_segments(path: Path, segments: list[Segment]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for segment in segments:
            payload = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": segment.confidence,
                "speaker": segment.speaker,
                "language": segment.language,
            }
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")
    logger.info("Wrote %s", path)


def _mark_job_finished(job_uuid: uuid.UUID, payload: Dict[str, Any]) -> None:
    with db_session() as session:
        job = session.get(TranscriptionJob, job_uuid)
        if not job:
            logger.error("Job %s missing when marking finished", job_uuid)
            return
        text_value = payload.get("text")
        if (not text_value or not text_value.strip()) and payload.get("txt_path"):
            try:
                text_value = Path(payload["txt_path"]).read_text(encoding="utf-8")
            except OSError as exc:  # pragma: no cover - defensive logging
                logger.warning("Unable to read transcript for job %s: %s", job_uuid, exc)
        job.status = JobStatus.finished
        job.text = text_value
        job.dialect_text = payload.get("dialect_text")
        job.output_txt_path = payload.get("txt_path")
        job.output_srt_path = payload.get("srt_path")
        job.output_vtt_path = payload.get("vtt_path")
        job.output_jsonl_path = payload.get("jsonl_path")
        job.error_message = None
        job.touch()
        session.commit()


def _mark_job_error(job_uuid: uuid.UUID, message: str) -> None:
    with db_session() as session:
        job = session.get(TranscriptionJob, job_uuid)
        if not job:
            logger.error("Job %s missing when marking error", job_uuid)
            return
        job.status = JobStatus.error
        job.error_message = message or "Unknown error"
        job.touch()
        session.commit()


def _format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")


def _to_srt(segments: list[Segment]) -> str:
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = _format_timestamp(segment.start)
        end = _format_timestamp(segment.end)
        speaker_prefix = f"{segment.speaker}: " if segment.speaker else ""
        lines.append(str(index))
        lines.append(f"{start} --> {end}")
        lines.append(f"{speaker_prefix}{segment.text}")
        lines.append("")
    return "\n".join(lines).strip()


def _to_vtt(segments: list[Segment]) -> str:
    lines = ["WEBVTT", ""]
    for segment in segments:
        start = _format_timestamp(segment.start).replace(",", ".")
        end = _format_timestamp(segment.end).replace(",", ".")
        speaker_prefix = f"{segment.speaker}: " if segment.speaker else ""
        lines.append(f"{start} --> {end}")
        lines.append(f"{speaker_prefix}{segment.text}")
        lines.append("")
    return "\n".join(lines).strip()


# Backward-compat alias used elsewhere in the codebase
process_transcription = transcribe_audio

__all__ = ["enqueue_transcription", "transcribe_audio", "process_transcription"]
