from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

try:
    import fasttext  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    fasttext = None


SUPPORTED_LANGS = {
    "th": "thai",
    "lo": "lao",
    "en": "english",
}


class LanguageIdentifier:
    def __init__(self, model_path: Optional[Path] = None) -> None:
        self.model = None
        if fasttext and model_path and Path(model_path).exists():
            self.model = fasttext.load_model(str(model_path))

    def detect(self, text: str, hint: Optional[str] = None) -> str:
        if hint:
            return hint
        cleaned = text.strip().lower()
        if not cleaned:
            return "th"
        if self.model:
            label, probability = self.model.predict(cleaned)
            if label:
                lang = label[0].split("__")[-1]
                return lang
        if re.search(r"[a-z]", cleaned):
            return "en"
        if any(word in cleaned for word in ["ซำ", "บ่", "เด้อ"]):
            return "lo"
        return "th"
