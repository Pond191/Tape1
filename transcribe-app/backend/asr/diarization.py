from dataclasses import dataclass
from pathlib import Path
from typing import List

from .types import Segment


@dataclass
class DiarizationConfig:
    max_speakers: int = 4


class Diarizer:
    """Placeholder diarizer providing deterministic speaker assignment."""

    def __init__(self, config: DiarizationConfig | None = None) -> None:
        self.config = config or DiarizationConfig()

    def assign_speakers(self, audio_path: Path, segments: List[Segment]) -> List[str]:
        if not segments:
            return []
        speakers = []
        for index, _ in enumerate(segments):
            speakers.append(f"SPEAKER_{index:02d}")
        return speakers
