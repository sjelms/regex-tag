from __future__ import annotations

import re
import subprocess
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub
from ftfy import fix_text

from .matching import detect_source_format

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
INLINE_NEWLINE_RE = re.compile(r"(?<!\n)\n(?!\n)")
WHITESPACE_RE = re.compile(r"[ \t]+")
BOILERPLATE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^jstor is a not-for-profit service",
        r"^your use of the jstor archive indicates",
        r"^for more information about jstor",
        r"^all use subject to https?://about\.jstor\.org/terms",
        r"^https?://about\.jstor\.org/terms$",
        r"^this content downloaded from$",
        r"^stable url:\s*https?://",
        r"downloaded from .* utc",
        r"collaborating with jstor to digitize, preserve and extend access",
    )
]


def _html_to_text(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    rendered = soup.get_text("\n")
    return _clean_extracted_text(rendered)


def _strip_markdown_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2].lstrip()


def _clean_line(line: str) -> str:
    cleaned = fix_text(line.replace("\u00ad", ""))
    cleaned = CONTROL_CHARS_RE.sub("", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def _looks_like_boilerplate(line: str) -> bool:
    if not line:
        return False
    return any(pattern.search(line) for pattern in BOILERPLATE_PATTERNS)


def _clean_extracted_text(text: str) -> str:
    fixed = fix_text((text or "").replace("\r\n", "\n").replace("\r", "\n"))
    fixed = fixed.replace("\u00ad", "")
    fixed = CONTROL_CHARS_RE.sub("", fixed)
    fixed = re.sub(r"(?<=\w)-\n(?=\w)", "", fixed)

    cleaned_lines: list[str] = []
    for raw_line in fixed.split("\n"):
        line = _clean_line(raw_line)
        if _looks_like_boilerplate(line):
            continue
        if line.startswith("http://") or line.startswith("https://"):
            continue
        cleaned_lines.append(line)

    collapsed = "\n".join(cleaned_lines)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    collapsed = INLINE_NEWLINE_RE.sub(" ", collapsed)
    collapsed = re.sub(r"\n\s+\n", "\n\n", collapsed)
    collapsed = WHITESPACE_RE.sub(" ", collapsed)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    return collapsed.strip()


def _extract_pdf_text(path: Path) -> str:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise RuntimeError(f"PDF source not found: {resolved}")
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(resolved))
        pages: list[str] = []
        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(text)
        content = "\n\n".join(pages).strip()
        if content:
            return _clean_extracted_text(content)
    except ImportError:
        pass

    command = ["mdls", "-raw", "-name", "kMDItemTextContent", str(resolved)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("No PDF extraction backend is available.") from exc

    content = (result.stdout or "").strip()
    if not content or content == "(null)":
        raise RuntimeError("Unable to extract text from PDF via pypdf or mdls.")
    return _clean_extracted_text(content)


def _extract_epub_archive(path: Path) -> str:
    book = epub.read_epub(str(path))
    chunks: list[str] = []
    seen_ids: set[str] = set()
    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ITEM_DOCUMENT:
            continue
        seen_ids.add(item.get_id())
        text = _html_to_text(item.get_content().decode("utf-8", errors="ignore"))
        if text:
            chunks.append(f"# {Path(item.file_name or item.get_name()).name}\n\n{text}")
    if not chunks:
        for item in book.get_items():
            if item.get_type() != ITEM_DOCUMENT or item.get_id() in seen_ids:
                continue
            text = _html_to_text(item.get_content().decode("utf-8", errors="ignore"))
            if text:
                chunks.append(f"# {Path(item.file_name or item.get_name()).name}\n\n{text}")
    if not chunks:
        raise RuntimeError("No XHTML/HTML files found in EPUB archive.")
    return "\n\n".join(chunks)


def _extract_epub_directory(path: Path) -> str:
    chunks: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
        if suffix not in {".xhtml", ".html", ".htm", ".md", ".markdown"}:
            continue
        raw = file_path.read_text(encoding="utf-8", errors="ignore")
        text = _clean_extracted_text(_strip_markdown_frontmatter(raw)) if suffix in {".md", ".markdown"} else _html_to_text(raw)
        if text:
            chunks.append(f"# {file_path.name}\n\n{text}")
    if not chunks:
        raise RuntimeError("No extractable markdown or XHTML files found in EPUB package directory.")
    return "\n\n".join(chunks)


def extract_to_markdown(source_path: Path) -> str:
    source_format = detect_source_format(source_path)
    if source_format == "markdown":
        return _clean_extracted_text(_strip_markdown_frontmatter(source_path.read_text(encoding="utf-8")))
    if source_format == "xhtml":
        return _html_to_text(source_path.read_text(encoding="utf-8", errors="ignore"))
    if source_format == "epub":
        return _extract_epub_archive(source_path)
    if source_format == "epub_package":
        return _extract_epub_directory(source_path)
    if source_format == "pdf":
        return _extract_pdf_text(source_path)
    raise RuntimeError(f"Unsupported extraction format: {source_format}")
