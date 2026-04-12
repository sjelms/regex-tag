from __future__ import annotations

import html
import re
import subprocess
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from .matching import detect_source_format


class _PlainTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "div", "section", "article", "br", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        text = " ".join(self.parts)
        text = html.unescape(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()


def _html_to_text(text: str) -> str:
    parser = _PlainTextHTMLParser()
    parser.feed(text)
    return parser.text()


def _strip_markdown_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2].lstrip()


def _extract_pdf_text(path: Path) -> str:
    command = ["mdls", "-raw", "-name", "kMDItemTextContent", str(path)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("No PDF extraction backend is available.") from exc

    content = (result.stdout or "").strip()
    if not content or content == "(null)":
        raise RuntimeError("Unable to extract text from PDF via mdls.")
    return content


def _extract_epub_archive(path: Path) -> str:
    chunks: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.lower().endswith((".xhtml", ".html", ".htm")):
                continue
            with archive.open(name) as handle:
                raw = handle.read().decode("utf-8", errors="ignore")
            text = _html_to_text(raw)
            if text:
                chunks.append(f"# {Path(name).name}\n\n{text}")
    if not chunks:
        raise RuntimeError("No XHTML/HTML files found in EPUB archive.")
    return "\n\n".join(chunks)


def _extract_epub_directory(path: Path) -> str:
    chunks: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        if not file_path.suffix.lower() in {".xhtml", ".html", ".htm", ".md", ".markdown"}:
            continue
        raw = file_path.read_text(encoding="utf-8", errors="ignore")
        text = raw if file_path.suffix.lower() in {".md", ".markdown"} else _html_to_text(raw)
        if text:
            chunks.append(f"# {file_path.name}\n\n{text}")
    if not chunks:
        raise RuntimeError("No extractable markdown or XHTML files found in EPUB package directory.")
    return "\n\n".join(chunks)


def extract_to_markdown(source_path: Path) -> str:
    source_format = detect_source_format(source_path)
    if source_format == "markdown":
        return _strip_markdown_frontmatter(source_path.read_text(encoding="utf-8"))
    if source_format == "xhtml":
        return _html_to_text(source_path.read_text(encoding="utf-8", errors="ignore"))
    if source_format == "epub":
        return _extract_epub_archive(source_path)
    if source_format == "epub_package":
        return _extract_epub_directory(source_path)
    if source_format == "pdf":
        return _extract_pdf_text(source_path)
    raise RuntimeError(f"Unsupported extraction format: {source_format}")
