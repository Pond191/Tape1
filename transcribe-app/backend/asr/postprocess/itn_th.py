import re
from typing import Optional


def inverse_text_normalize(text: str, language: str = "th") -> str:
    if not text:
        return text
    if language.startswith("th"):
        text = _normalize_time(text)
        text = _normalize_currency(text)
    return text


def _normalize_time(text: str) -> str:
    pattern = re.compile(r"(\d{1,2})[:.](\d{2})")
    return pattern.sub(lambda m: f"{m.group(1)}โมง{m.group(2)}", text)


def _normalize_currency(text: str) -> str:
    pattern = re.compile(r"(\d+[.,]?\d*)\s?(บาท|฿)")
    return pattern.sub(lambda m: f"{m.group(1)}บาท", text)
