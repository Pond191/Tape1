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
    job_id = response.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    if status["status"] != "finished":
        status = client.get(f"/api/jobs/{job_id}").json()
    assert status["status"] == "finished"

    result = client.get(f"/api/jobs/{job_id}/result/inline").json()
    assert "ทำ" in (result.get("dialect_mapped_text") or "")
    assert result["metadata"]["original_filename"] == "ฝึกพูดภาษาอีสาน EP3.mp3"

    download = client.get(f"/api/jobs/{job_id}/srt")
    assert download.status_code == 200

    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["text"]
    txt_path = Path(status["output_txt_path"])
    assert txt_path.exists()
    assert txt_path.name == "transcript.txt"
    jsonl_path = Path(status["output_jsonl_path"])
    assert jsonl_path.exists()
    assert jsonl_path.name == "segments.jsonl"


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
    job_id = response.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    if status["status"] == "pending":
        status = client.get(f"/api/jobs/{job_id}").json()

    assert status["status"] == "finished"


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
