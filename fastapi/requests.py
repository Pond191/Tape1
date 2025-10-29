from __future__ import annotations

from io import BytesIO
from typing import BinaryIO


class UploadFile:
    def __init__(self, filename: str, file: BinaryIO | None = None) -> None:
        self.filename = filename
        self.file = file or BytesIO()

    async def read(self) -> bytes:
        return self.file.read()
