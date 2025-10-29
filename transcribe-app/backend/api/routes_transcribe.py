from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from ..core.config import get_settings
from ..core.logging import logger
from ..db.models import TranscriptionJob
from ..db.schema import JobCreateResponse
from ..db.session import get_session
from ..workers.tasks import enqueue_transcription

router = APIRouter()
settings = get_settings()


@router.post("/transcribe", response_model=JobCreateResponse)
async def create_transcription_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: str = Form("{}"),
    session = Depends(get_session),
) -> JobCreateResponse:
    try:
        payload: Dict[str, Any] = json.loads(options) if options else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid options JSON") from exc

    job_id = str(uuid.uuid4())
    job_dir = Path(settings.storage_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(file.filename or "audio.wav")
    audio_path = job_dir / filename.name

    with audio_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    source_path_value = getattr(file.file, "name", None)
    if isinstance(source_path_value, str) and source_path_value:
        source_path = Path(source_path_value)
        if source_path.exists():
            sidecar = source_path.with_suffix(".json")
            if sidecar.exists():
                shutil.copy(sidecar, audio_path.with_suffix(".json"))

    payload.update({"audio_path": str(audio_path)})

    job = TranscriptionJob(
        id=job_id,
        filename=filename.name,
        model_size=payload.get("model_size", settings.default_model_size),
        options=payload,
    )
    session.add(job)
    session.flush()

    background_tasks.add_task(enqueue_transcription, job_id)
    logger.info("Created transcription job %s for %s", job_id, filename.name)

    return JobCreateResponse(job_id=job_id)
