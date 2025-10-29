import json
import os
from pathlib import Path
import importlib

from fastapi.testclient import TestClient


def setup_app(tmp_path):
    storage_dir = tmp_path / "storage"
    db_path = tmp_path / "db.sqlite"
    os.environ["TRANSCRIBE_STORAGE_DIR"] = str(storage_dir)
    os.environ["TRANSCRIBE_DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    os.environ["CELERY_EAGER"] = "1"

    from backend.core import config

    config.get_settings.cache_clear()
    session_module = importlib.import_module("backend.db.session")
    importlib.reload(session_module)
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
    options = {
        "model_size": "tiny",
        "enable_diarization": True,
        "enable_dialect_map": True,
        "custom_lexicon": ["Node-RED", "MQTT", "สงขลานครินทร์"],
    }

    response = client.post(
        "/api/transcribe",
        files={"file": ("sample.wav", audio_path.open("rb"), "audio/wav")},
        data={"options": json.dumps(options)},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    if status["status"] != "finished":
        status = client.get(f"/api/jobs/{job_id}").json()
    assert status["status"] == "finished"

    result = client.get(f"/api/jobs/{job_id}/result/inline").json()
    assert "ทำ" in (result.get("dialect_mapped_text") or "")

    download = client.get(f"/api/jobs/{job_id}/result", params={"format": "srt"})
    assert download.status_code == 200


def test_upload_handles_missing_underlying_name(tmp_path):
    app = setup_app(tmp_path)
    client = TestClient(app)

    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"fake mp3 data")

    response = client.post(
        "/api/transcribe",
        files={"file": ("sample.mp3", audio_path.open("rb"), "audio/mpeg")},
        data={"options": json.dumps({})},
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    if status["status"] == "pending":
        status = client.get(f"/api/jobs/{job_id}").json()

    assert status["status"] == "finished"
