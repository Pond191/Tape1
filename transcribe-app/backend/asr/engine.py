# backend/asr/engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Protocol
from pathlib import Path

# from faster_whisper import WhisperModel

from .types import Segment  # dataclass: start, end, text, confidence, speaker, language
from ..core.config import get_settings
from ..core.logging import logger


@dataclass
class TranscriptionOptions:
    model_size: str
    enable_dialect_map: bool = False
    language: Optional[str] = None          # None = auto
    vad_filter: bool = False                # จะเปิดก็ได้ ถ้าต้องการตัดช่วงเงียบด้วย fp32


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
        # <-- ทำ lazy import ตรงนี้แทน
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
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)


# ===== Factory =====

_engine_singleton: Optional[_FastWhisperEngine] = None

def load_engine() -> ASREngine:
    """
    โหลด engine แบบ singleton — อ่านค่า default model จาก settings
    """
    global _engine_singleton
    if _engine_singleton is None:
        settings = get_settings()
        # ตั้งค่า device/compute type ได้ด้วย env:
        #   TRANSCRIBE_DEVICE = "cpu" หรือ "cuda"
        #   TRANSCRIBE_COMPUTE = "int8"|"int8_float16"|"float16"|"float32"
        import os
        device = os.getenv("TRANSCRIBE_DEVICE", "cpu")
        compute = os.getenv("TRANSCRIBE_COMPUTE", "int8")
        _engine_singleton = _FastWhisperEngine(
            model_size=settings.default_model_size,
            device=device,
            compute_type=compute,
        )
    return _engine_singleton
