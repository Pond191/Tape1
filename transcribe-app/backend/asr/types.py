from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Segment:
    start: float
    end: float
    text: str
    confidence: float
    speaker: Optional[str] = None
    language: Optional[str] = None
    words: List[Dict[str, float]] = field(default_factory=list)
