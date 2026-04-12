from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"[^a-z0-9]+", " ", ascii_value)
    return re.sub(r"\s+", " ", ascii_value).strip()


def first_year(value: str | None) -> str:
    if not value:
        return ""
    match = re.search(r"(19|20)\d{2}", value)
    return match.group(0) if match else ""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sentence_split(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]


def bullet_list(text: str, count: int = 3) -> list[str]:
    sentences = sentence_split(text)
    return sentences[:count]


def ensure_suffix_link(citekey: str) -> str:
    return f"[[{citekey}_wiki]]"

