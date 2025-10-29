from __future__ import annotations

from pathlib import Path
from typing import Optional


class FileResponse:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def read(self) -> bytes:
        return self.path.read_bytes()
