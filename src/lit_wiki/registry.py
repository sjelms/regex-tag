from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import SourceRecord


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SourceRegistry:
    def __init__(self, path: Path, records: dict[str, SourceRecord]) -> None:
        self.path = path
        self.records = records

    @classmethod
    def load(cls, path: Path) -> "SourceRegistry":
        if not path.exists():
            return cls(path, {})
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        records = {citekey: SourceRecord.from_dict(data) for citekey, data in raw.get("sources", {}).items()}
        return cls(path, records)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sources": {citekey: record.as_dict() for citekey, record in sorted(self.records.items())},
        }
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    def upsert(self, record: SourceRecord) -> SourceRecord:
        now = utc_now_iso()
        existing = self.records.get(record.citekey)
        if existing:
            record.registered_at = existing.registered_at or now
        else:
            record.registered_at = now
        record.updated_at = now
        self.records[record.citekey] = record
        return record

    def get(self, citekey: str) -> SourceRecord | None:
        return self.records.get(citekey)

