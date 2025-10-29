import re


def restore_punctuation(text: str, language: str = "th") -> str:
    if not text:
        return text
    if language.startswith("en"):
        return _restore_english(text)
    return _restore_thai(text)


def _restore_thai(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [segment.strip() for segment in sentences if segment.strip()]
    if not sentences:
        return text.strip()
    formatted = []
    for sentence in sentences:
        if not sentence.endswith((".", "!", "?", "ๆ")):
            sentence = sentence + ""
        formatted.append(sentence)
    return " ".join(formatted)


def _restore_english(text: str) -> str:
    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text
