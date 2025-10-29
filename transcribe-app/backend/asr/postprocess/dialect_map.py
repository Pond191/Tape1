from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable


DEFAULT_MAPPING: Dict[str, Dict[str, str]] = {
    "north": {
        "ยะ": "นะ",
        "กึ๊ด": "คิด",
        "ละอ่อน": "เด็ก",
    },
    "isan": {
        "อยู่จักได๋": "อยู่ที่ไหน",
        "กินเข่า": "กินข้าว",
        "เฮ็ด": "ทำ",
    },
    "south": {
        "ม่ายหล่าว": "ไม่หรอก",
        "เหลย": "เลย",
        "แลน": "วิ่ง",
    },
}


@dataclass
class DialectMapper:
    custom_tables: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def load_csv(self, csv_path: Path) -> None:
        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                region = row.get("dialect", "").strip().lower()
                source = row.get("source", "").strip()
                target = row.get("target", "").strip()
                if not region or not source or not target:
                    continue
                self.custom_tables.setdefault(region, {})[source] = target

    def map_text(self, text: str, region: str | None = None) -> str:
        tables = DEFAULT_MAPPING.copy()
        for key, values in self.custom_tables.items():
            tables.setdefault(key, {}).update(values)
        segments = text.split()
        mapped_tokens = []
        for token in segments:
            replacement = None
            if region:
                region = region.lower()
                replacement = tables.get(region, {}).get(token)
            else:
                for region_map in tables.values():
                    if token in region_map:
                        replacement = region_map[token]
                        break
            mapped_tokens.append(replacement or token)
        return " ".join(mapped_tokens)
