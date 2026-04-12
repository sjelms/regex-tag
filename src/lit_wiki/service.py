from __future__ import annotations

from pathlib import Path

from .bibliography import BibliographyIndex, parse_bibliography, write_registry
from .config import AppConfig, ensure_runtime_directories
from .extraction import extract_to_markdown
from .matching import detect_source_format, match_source
from .models import MatchResult, SourceRecord
from .notes import render_note, source_note_path
from .providers import generate_sections
from .registry import SourceRegistry
from .utils import file_sha256
from .wiki import (
    build_graph,
    ensure_person_pages,
    lint_wiki,
    update_index,
    update_log,
    update_overview,
)


def load_bibliography(config: AppConfig) -> BibliographyIndex:
    return parse_bibliography(config.bibliography_file)


def sync_bibliography(config: AppConfig) -> BibliographyIndex:
    ensure_runtime_directories(config)
    bibliography = load_bibliography(config)
    write_registry(bibliography, config.bibliography_registry_file)
    return bibliography


def register_source(
    config: AppConfig,
    source_path: Path,
    citekey: str | None = None,
) -> tuple[SourceRecord, MatchResult]:
    ensure_runtime_directories(config)
    bibliography = load_bibliography(config)
    registry = SourceRegistry.load(config.registry_file)

    match = MatchResult(citekey=citekey or "", confidence=1.0 if citekey else 0.0, reason="manual citekey", needs_review=False)
    if citekey:
        if bibliography.get(citekey) is None:
            raise ValueError(f"Unknown citekey: {citekey}")
    else:
        match = match_source(source_path, bibliography)
        if not match.citekey:
            raise ValueError(f"Unable to determine citekey for '{source_path}' ({match.reason})")

    record = SourceRecord(
        citekey=match.citekey,
        source_path=str(source_path),
        source_format=detect_source_format(source_path),
        raw_hash=file_sha256(source_path) if source_path.is_file() else "",
        match_reason=match.reason,
        confidence=match.confidence,
        needs_review=match.needs_review,
    )
    registry.upsert(record)
    registry.save()
    return record, match


def extract_source(config: AppConfig, citekey: str) -> SourceRecord:
    ensure_runtime_directories(config)
    registry = SourceRegistry.load(config.registry_file)
    record = registry.get(citekey)
    if record is None:
        raise ValueError(f"No registered source for citekey '{citekey}'")

    extracted_text = extract_to_markdown(Path(record.source_path))
    output_path = config.extracted_dir / f"{citekey}.md"
    output_path.write_text(extracted_text, encoding="utf-8")
    record.extracted_path = str(output_path)
    record.extraction_status = "extracted"
    record.ingest_status = "registered"
    registry.upsert(record)
    registry.save()
    return record


def ingest_source(config: AppConfig, citekey: str) -> Path:
    ensure_runtime_directories(config)
    bibliography = load_bibliography(config)
    entry = bibliography.get(citekey)
    if entry is None:
        raise ValueError(f"Unknown citekey: {citekey}")

    registry = SourceRegistry.load(config.registry_file)
    record = registry.get(citekey)
    if record is None:
        raise ValueError(f"No registered source for citekey '{citekey}'")

    extracted_text = ""
    if record.extracted_path:
        extracted_file = Path(record.extracted_path)
        if extracted_file.exists():
            extracted_text = extracted_file.read_text(encoding="utf-8")
    sections, provider_used = generate_sections(config, entry, extracted_text, bibliography)

    note_path = source_note_path(config.wiki_sources_dir, citekey)
    existing = note_path.read_text(encoding="utf-8") if note_path.exists() else None
    note_path.write_text(render_note(entry, record, sections, existing_note=existing), encoding="utf-8")

    record.provider = provider_used
    record.ingest_status = "ingested"
    registry.upsert(record)
    registry.save()

    ensure_person_pages(config, entry)
    update_index(config, entry)
    update_log(config, entry)
    update_overview(config, bibliography)
    return note_path


def ingest_batch(config: AppConfig) -> list[Path]:
    registry = SourceRegistry.load(config.registry_file)
    ingested: list[Path] = []
    for citekey, record in sorted(registry.records.items()):
        if record.extraction_status != "extracted":
            continue
        ingested.append(ingest_source(config, citekey))
    return ingested


def run_graph_build(config: AppConfig) -> tuple[int, int]:
    ensure_runtime_directories(config)
    return build_graph(config)


def run_lint(config: AppConfig) -> str:
    ensure_runtime_directories(config)
    report = lint_wiki(config)
    report_path = config.wiki_dir / "lint-report.md"
    report_path.write_text(report, encoding="utf-8")
    return report
