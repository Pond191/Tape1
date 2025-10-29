import os
from pathlib import Path

os.environ.setdefault("TRANSCRIBE_STORAGE_DIR", "./test-storage")

from backend.asr.engine import ASREngine, TranscriptionOptions


def test_transcription_pipeline(tmp_path):
    engine = ASREngine()
    fixtures_dir = Path(__file__).parent / "data"

    # Create a temporary placeholder audio file to avoid storing binary assets in the repo.
    audio_path = tmp_path / "sample.wav"
    audio_path.write_text("dummy audio", encoding="utf-8")

    # The dummy backend reads an adjacent JSON file to obtain deterministic segments.
    transcript_payload = (fixtures_dir / "sample.json").read_text(encoding="utf-8")
    (tmp_path / "sample.json").write_text(transcript_payload, encoding="utf-8")

    result = engine.transcribe(audio_path, TranscriptionOptions(enable_dialect_map=True))

    assert result.text
    assert result.segments
    assert result.segments[0].speaker is not None
    assert result.dialect_mapped_text is not None
    assert "ทำ" in result.dialect_mapped_text
