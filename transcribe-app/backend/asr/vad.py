from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .types import Segment


@dataclass
class VADConfig:
    frame_duration: int = 30
    aggressiveness: int = 2


class VADSegmenter:
    """Simple placeholder VAD that returns existing segments or a single chunk."""

    def __init__(self, config: VADConfig | None = None) -> None:
        self.config = config or VADConfig()

    def segment(self, audio_path: Path) -> List[Segment]:
        # In the dummy implementation we delegate to the ASR backend, so VAD simply
        # returns one placeholder segment describing the whole file.
        return [Segment(start=0.0, end=5.0, text="", confidence=1.0)]

    def iterate_frames(self, audio_path: Path) -> Iterable[bytes]:
        # Placeholder for streaming support.
        yield b""
