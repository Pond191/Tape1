import io
import json
import os
from pathlib import Path
import importlib

from fastapi.testclient import TestClient


def setup_app(tmp_path, max_upload_mb: int = 200):
    storage_dir = tmp_path / "storage"
    db_path = tmp_path / "db.sqlite"
    os.environ["TRANSCRIBE_STORAGE_DIR"] = str(storage_dir)
    os.environ["TRANSCRIBE_DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    os.environ["CELERY_EAGER"] = "1"
    os.environ["MAX_UPLOAD_MB"] = str(max_upload_mb)
    os.environ["TRANSCRIBE_ASR_BACKEND"] = "dummy"

    from backend.core import config

    config.get_settings.cache_clear()
    session_module = importlib.import_module("backend.db.session")
    importlib.reload(session_module)
    routes_module = importlib.import_module("backend.api.routes_transcribe")
    importlib.reload(routes_module)
    routes_module.settings.max_upload_mb = max_upload_mb
    app_module = importlib.import_module("backend.app")
    importlib.reload(app_module)
    return app_module.app


def test_create_and_retrieve_job(tmp_path):
    app = setup_app(tmp_path)
    client = TestClient(app)

    fixtures_dir = Path(__file__).parent / "data"
    audio_path = tmp_path / "sample.wav"
    audio_path.write_text("dummy audio", encoding="utf-8")

    sample_json = fixtures_dir / "sample.json"
    transcript_path = tmp_path / "sample.json"
    transcript_path.write_text(sample_json.read_text(encoding="utf-8"), encoding="utf-8")
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "ฝึกพูดภาษาอีสาน EP3.mp3",
                audio_path.open("rb"),
                "audio/mpeg",
            )
        },
        data={
            "model_size": "tiny",
            "enable_dialect_map": "true",
            "enable_diarization": "true",
            "enable_punct": "true",
            "enable_itn": "true",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    job_id = payload.get("id") or payload.get("job_id")

    def _poll():
        return client.get(f"/api/jobs/{job_id}").json()

    status = _poll()
    if status["status"] != "finished":
        status = _poll()
    assert status["status"] == "finished"
    assert status.get("dialect_text")
    assert "ทำ" in (status.get("dialect_text") or "")
    assert status.get("original_filename") == "ฝึกพูดภาษาอีสาน EP3.mp3"

    download = client.get(f"/api/jobs/{job_id}/srt")
    assert download.status_code == 200

    files = status.get("files") or {}
    assert files.get("txt") and files.get("jsonl")

    storage_dir = Path(os.environ["TRANSCRIBE_STORAGE_DIR"]) / "jobs" / str(job_id)
    txt_path = storage_dir / "transcript.txt"
    assert txt_path.exists()
    jsonl_path = storage_dir / "segments.jsonl"
    assert jsonl_path.exists()


def test_upload_handles_missing_underlying_name(tmp_path):
    app = setup_app(tmp_path)
    client = TestClient(app)

    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"fake mp3 data")

    response = client.post(
        "/api/upload",
        files={"file": ("sample.mp3", audio_path.open("rb"), "audio/mpeg")},
        data={
            "model_size": "small",
            "enable_dialect_map": "false",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    job_id = payload.get("id") or payload.get("job_id")

    status = client.get(f"/api/jobs/{job_id}").json()
    if status["status"] == "pending":
        status = client.get(f"/api/jobs/{job_id}").json()

    assert status["status"] in {"running", "finished"}


def test_upload_rejects_large_file(tmp_path):
    app = setup_app(tmp_path, max_upload_mb=1)
    client = TestClient(app)

    payload = io.BytesIO(b"0" * (2 * 1024 * 1024))
    payload.name = "huge.wav"

    response = client.post(
        "/api/upload",
        files={"file": (payload.name, payload, "audio/wav")},
        data={"model_size": "small"},
    )

    assert response.status_code == 413
    assert "สูงสุด 1 MB" in (_extract_message(response) or "")


def test_upload_rejects_invalid_type(tmp_path):
    app = setup_app(tmp_path)
    client = TestClient(app)

    payload = io.BytesIO(b"123")
    payload.name = "notes.txt"

    response = client.post(
        "/api/upload",
        files={"file": (payload.name, payload, "text/plain")},
        data={"model_size": "small"},
    )

    assert response.status_code == 415
    assert _extract_message(response) == "ชนิดไฟล์ไม่รองรับ"
def _extract_message(response):
    payload = response.json()
    if isinstance(payload, dict):
        if "message" in payload:
            return payload["message"]
        detail = payload.get("detail")
        if isinstance(detail, dict) and "message" in detail:
            return detail["message"]
    return None
