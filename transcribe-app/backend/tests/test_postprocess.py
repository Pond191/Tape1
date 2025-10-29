from backend.asr.postprocess.dialect_map import DialectMapper
from backend.asr.postprocess.itn_th import inverse_text_normalize
from backend.asr.postprocess.normalize_th import normalize_text
from backend.asr.postprocess.punct_restore import restore_punctuation


def test_normalize_numbers():
    assert normalize_text("ประชุม 15.30", "th") == "ประชุม สิบห้าโมงสามสิบ"


def test_inverse_text_normalize_time():
    assert "โมง" in inverse_text_normalize("เริ่ม 10:30", "th")


def test_restore_punctuation():
    assert restore_punctuation("สวัสดีครับ ยินดีต้อนรับ", "th").startswith("สวัสดีครับ")


def test_dialect_mapper_default():
    mapper = DialectMapper()
    assert mapper.map_text("เฮ็ด งาน อยู่จักได๋").startswith("ทำ")
