#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from jiwer import cer, wer

from backend.asr.engine import ASREngine, TranscriptionOptions


def load_reference(audio_path: Path) -> str:
    transcript_file = audio_path.with_suffix(".json")
    if not transcript_file.exists():
        return ""
    payload = json.loads(transcript_file.read_text(encoding="utf-8"))
    return " ".join(segment["text"] for segment in payload.get("segments", []))


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark transcription pipeline")
    parser.add_argument("audio", type=Path, help="Audio file to transcribe")
    parser.add_argument("--model-size", default="small")
    args = parser.parse_args()

    engine = ASREngine()
    options = TranscriptionOptions(model_size=args.model_size)

    start = time.time()
    result = engine.transcribe(args.audio, options)
    duration = time.time() - start

    reference = load_reference(args.audio)
    hypothesis = result.text
    word_error = wer(reference, hypothesis) if reference else None
    char_error = cer(reference, hypothesis) if reference else None

    print("Audio:", args.audio)
    print("Duration (s):", duration)
    if reference:
        print("WER:", word_error)
        print("CER:", char_error)
    print("RTF:", duration / max(result.segments[-1].end if result.segments else 1.0, 1.0))


if __name__ == "__main__":
    main()
