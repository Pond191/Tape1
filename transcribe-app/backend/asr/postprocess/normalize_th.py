import re
from typing import Dict

THAI_ONES = {
    0: "ศูนย์",
    1: "หนึ่ง",
    2: "สอง",
    3: "สาม",
    4: "สี่",
    5: "ห้า",
    6: "หก",
    7: "เจ็ด",
    8: "แปด",
    9: "เก้า",
}

THAI_TENS = {
    0: "",
    1: "สิบ",
    2: "ยี่สิบ",
    3: "สามสิบ",
    4: "สี่สิบ",
    5: "ห้าสิบ",
    6: "หกสิบ",
    7: "เจ็ดสิบ",
    8: "แปดสิบ",
    9: "เก้าสิบ",
}


def _two_digit(number: int) -> str:
    if number < 10:
        return THAI_ONES[number]
    if number == 10:
        return "สิบ"
    if number < 20:
        if number == 11:
            return "สิบเอ็ด"
        return "สิบ" + THAI_ONES[number - 10]
    tens = number // 10
    ones = number % 10
    if ones == 0:
        return THAI_TENS.get(tens, "")
    ones_word = "เอ็ด" if ones == 1 else THAI_ONES.get(ones, "")
    return THAI_TENS.get(tens, "") + (ones_word or "")


def _number_to_words(number: int) -> str:
    if number < 100:
        return _two_digit(number)
    if number < 1000:
        hundreds = number // 100
        remainder = number % 100
        parts = [THAI_ONES.get(hundreds, "") + "ร้อย"]
        if remainder:
            parts.append(_two_digit(remainder))
        return "".join(parts)
    return str(number)


def normalize_text(text: str, language: str = "th") -> str:
    normalized = text
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return normalized
    if language.startswith("th"):
        normalized = re.sub(
            r"(\d{1,2})[.:](\d{2})",
            lambda m: f"{_number_to_words(int(m.group(1)))}โมง{_number_to_words(int(m.group(2)))}",
            normalized,
        )
        normalized = re.sub(
            r"(\d{1,3})",
            lambda m: _number_to_words(int(m.group(1))),
            normalized,
        )
    return normalized
