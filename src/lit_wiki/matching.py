from __future__ import annotations

import plistlib
import re
import zipfile
from pathlib import Path

import yaml

from .bibliography import BibliographyIndex
from .models import MatchResult
from .utils import normalize_text


PDF_PATTERN = re.compile(r"^(?P<title>.+)_(?P<authors>.+)_(?P<year>(19|20)\d{2})$")


def detect_source_format(path: Path) -> str:
    if path.is_dir():
        if (path / "iTunesMetadata.plist").exists():
            return "epub_package"
        return "directory"
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".epub":
        return "epub"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix in {".xhtml", ".html", ".htm"}:
        return "xhtml"
    return suffix.lstrip(".") or "unknown"


def _clean_citekey(value: str) -> str:
    return value.strip().replace("[[@", "").replace("]]", "").replace("@", "")


def extract_citation_key_from_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    frontmatter = yaml.safe_load(parts[1]) or {}
    for key in ("citation-key", "citation_key", "citekey", "key"):
        value = frontmatter.get(key)
        if isinstance(value, str) and value.strip():
            return _clean_citekey(value)
    return ""


def extract_citation_key_from_epub_metadata(path: Path) -> str:
    payload: dict[str, object] | None = None
    if path.is_dir():
        plist_path = path / "iTunesMetadata.plist"
        if not plist_path.exists():
            return ""
        with plist_path.open("rb") as handle:
            payload = plistlib.load(handle)
    elif path.suffix.lower() == ".epub":
        with zipfile.ZipFile(path) as archive:
            try:
                with archive.open("iTunesMetadata.plist") as handle:
                    payload = plistlib.loads(handle.read())
            except KeyError:
                return ""
    if not payload:
        return ""
    artist_name = str(payload.get("artistName", "")).strip()
    if not artist_name:
        return ""
    parts = [part.strip() for part in artist_name.split(",") if part.strip()]
    candidate = parts[-1] if parts else ""
    if re.fullmatch(r"[A-Za-z0-9:-]+", candidate):
        return _clean_citekey(candidate)
    return ""


def match_markdown_source(path: Path, bibliography: BibliographyIndex) -> MatchResult:
    citation_key = extract_citation_key_from_markdown(path)
    if citation_key and bibliography.get(citation_key):
        return MatchResult(citekey=citation_key, confidence=1.0, reason="markdown citation-key", needs_review=False)
    return MatchResult(reason="markdown citation-key missing or unknown", needs_review=True)


def match_epub_source(path: Path, bibliography: BibliographyIndex) -> MatchResult:
    citation_key = extract_citation_key_from_epub_metadata(path)
    if citation_key and bibliography.get(citation_key):
        return MatchResult(citekey=citation_key, confidence=1.0, reason="epub metadata citekey", needs_review=False)
    return MatchResult(reason="epub metadata citekey missing or unknown", needs_review=True)


def parse_pdf_filename(path: Path) -> tuple[str, list[str], str] | None:
    match = PDF_PATTERN.match(path.stem)
    if not match:
        return None
    authors = [part.strip() for part in match.group("authors").split(",") if part.strip()]
    return match.group("title"), authors, match.group("year")


def match_pdf_source(path: Path, bibliography: BibliographyIndex) -> MatchResult:
    parsed = parse_pdf_filename(path)
    if not parsed:
        return MatchResult(reason="pdf filename did not match convention", needs_review=True)

    title, author_surnames, year = parsed
    match = bibliography.find_by_title_authors_year(title, author_surnames, year)
    if match:
        confidence = 0.98 if normalize_text(match.title) == normalize_text(title) else 0.75
        return MatchResult(
            citekey=match.citekey,
            confidence=confidence,
            reason="pdf filename title/authors/year",
            needs_review=confidence < 0.9,
        )
    return MatchResult(reason="no bibliography match for pdf filename", needs_review=True)


def match_source(path: Path, bibliography: BibliographyIndex) -> MatchResult:
    source_format = detect_source_format(path)
    if source_format == "markdown":
        return match_markdown_source(path, bibliography)
    if source_format in {"epub", "epub_package"}:
        return match_epub_source(path, bibliography)
    if source_format == "pdf":
        return match_pdf_source(path, bibliography)
    return MatchResult(reason=f"unsupported source format for deterministic matching: {source_format}", needs_review=True)

