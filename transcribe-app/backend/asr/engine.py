from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Protocol
from pathlib import Path

from .types import Segment
from ..core.config import get_settings
from ..core.logging import logger


@dataclass
class TranscriptionOptions:
    model_size: str
    enable_dialect_map: bool = False
    language: Optional[str] = None
    vad_filter: bool = False
    compute_type: Optional[str] = None


class ASREngine(Protocol):
    def transcribe(self, audio_path: Path, options: TranscriptionOptions):
        ...


@dataclass
class _Result:
    text: str
    segments: List[Segment]
    dialect_mapped_text: Optional[str] = None


class _FastWhisperEngine:
    def __init__(self, model_size: str, device: Optional[str] = None, compute_type: str = "int8"):
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "faster-whisper is not available in this image. "
                "Please ensure it is in requirements.txt AND the image has libgomp1 installed."
            ) from e

        if device is None:
            import os
            device = os.getenv("TRANSCRIBE_DEVICE", "cpu")

        logger.info("Loading faster-whisper model=%s device=%s compute_type=%s", model_size, device, compute_type)
        self._WhisperModel = WhisperModel
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: Path, options: TranscriptionOptions) -> _Result:
        language = options.language
        vad_filter = bool(options.vad_filter)

        segments_iter, info = self._model.transcribe(
            str(audio_path),
            language=language,         # None = auto
            vad_filter=vad_filter,
        )

        if not isinstance(segments_iter, Iterable):
            segments_list = list(segments_iter or [])
        else:
            segments_list = list(segments_iter)

        out_segments: List[Segment] = []
        for s in segments_list:
            text = (getattr(s, "text", "") or "").strip()
            start = float(getattr(s, "start", 0.0) or 0.0)
            end = float(getattr(s, "end", 0.0) or 0.0)
            avg_logprob = getattr(s, "avg_logprob", None)
            conf = 0.0
            if isinstance(avg_logprob, (int, float)):
                conf = max(0.0, min(1.0, 1.0 + float(avg_logprob)))

            out_segments.append(
                Segment(
                    start=start,
                    end=end,
                    text=text,
                    confidence=conf,
                    speaker=None,
                    language=getattr(info, "language", None),
                )
            )

        full_text = "\n".join([seg.text for seg in out_segments if seg.text]).strip()
        dialect_text = None
        if options.enable_dialect_map and full_text:
            dialect_text = None  # hook เผื่อคุณต่อยอด mapping ภาษาถิ่น

        return _Result(text=full_text, segments=out_segments, dialect_mapped_text=dialect_text)


# ===== Factory (singleton) =====
_engine_singleton: Optional[_FastWhisperEngine] = None

def load_engine() -> ASREngine:
    global _engine_singleton
    if _engine_singleton is None:
        settings = get_settings()
        import os
        device = os.getenv("TRANSCRIBE_DEVICE", "cpu")
        compute = os.getenv("TRANSCRIBE_COMPUTE", "int8")
        _engine_singleton = _FastWhisperEngine(
            model_size=settings.default_model_size,
            device=device,
            compute_type=compute,
        )
    return _engine_singleton
