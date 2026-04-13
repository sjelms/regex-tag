from __future__ import annotations

import re
import traceback
from pathlib import Path

from .bibliography import BibliographyIndex, parse_bibliography, write_registry
from .budget import load_budget_ledger
from .config import AppConfig, ensure_runtime_directories
from .extraction import extract_to_markdown
from .matching import detect_source_format, match_source
from .models import MatchResult, SourceRecord, WatchSummary
from .notes import render_note, source_note_path
from .providers import generate_sections, run_approved_fallback
from .registry import SourceRegistry, utc_now_iso
from .utils import file_sha256
from .watch import (
    archive_watch_item,
    iter_watch_items,
    resolve_fallback_approval,
    show_fallback_complete_dialog,
    show_final_dialog,
    show_info_dialog,
    timed_watch_run,
)
from .wiki import (
    build_graph,
    ensure_concept_pages,
    ensure_person_pages,
    lint_wiki,
    update_index,
    update_log,
    update_overview,
)

RAW_SOURCE_FORMATS = {"pdf", "epub", "epub_package", "markdown", "xhtml", "html", "htm"}
EXTRACTION_ARTIFACT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"this content downloaded from",
        r"all use subject to https?://about\.jstor\.org/terms",
        r"your use of the jstor archive indicates",
        r"jstor is a not-for-profit service",
    )
]


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
    resolved_source = source_path.expanduser().resolve()
    if _is_raw_source_under_wiki(config, resolved_source):
        raise ValueError("Raw source files must be placed in the watch folder, not under wiki/.")

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
        processing_state="registered",
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
    record.processing_state = "extracted"
    registry.upsert(record)
    registry.save()
    return record


def _save_record(config: AppConfig, record: SourceRecord) -> SourceRecord:
    registry = SourceRegistry.load(config.registry_file)
    registry.upsert(record)
    registry.save()
    return record


def _load_record(config: AppConfig, citekey: str) -> SourceRecord:
    registry = SourceRegistry.load(config.registry_file)
    record = registry.get(citekey)
    if record is None:
        raise ValueError(f"No registered source for citekey '{citekey}'")
    return record


def _is_raw_source_under_wiki(config: AppConfig, source_path: Path) -> bool:
    try:
        relative = source_path.resolve().relative_to(config.wiki_dir.resolve())
    except ValueError:
        return False
    source_format = detect_source_format(source_path)
    if source_format not in RAW_SOURCE_FORMATS:
        return False
    return relative.suffix.lower() != ".md" or not relative.name.endswith("_wiki.md")


def _validate_publishable_note(
    config: AppConfig,
    entry,
    bibliography: BibliographyIndex,
    extracted_text: str,
    sections: dict[str, object],
) -> str:
    def string_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(item) for item in value if str(item).strip()]

    for pattern in EXTRACTION_ARTIFACT_PATTERNS:
        if pattern.search(extracted_text):
            return "extraction contamination detected"
    if any(ord(char) < 32 and char not in "\n\t\r" for char in extracted_text):
        return "extraction contains control characters"

    related_refs = [
        str(item).replace("[[@", "").replace("]]", "").replace("@", "").strip()
        for item in string_list(sections.get("related_references", []))
        if str(item).strip()
    ]
    for citekey in related_refs:
        candidate = bibliography.get(citekey)
        if candidate is None:
            return f"broken bibliography key in Related References: {citekey}"
        if candidate.year and entry.year and candidate.year > entry.year:
            return f"future-dated related reference detected: {citekey}"

    if len(string_list(sections.get("keyword_tags", []))) > config.keyword_policy.max_metadata_tags:
        return "keyword tag enrichment exceeded configured cap"
    if len(string_list(sections.get("see_also_links", []))) > config.keyword_policy.max_see_also_links:
        return "see also enrichment exceeded configured cap"
    return ""


def ingest_source(config: AppConfig, citekey: str, approval_resolver=None) -> Path:
    ensure_runtime_directories(config)
    bibliography = load_bibliography(config)
    entry = bibliography.get(citekey)
    if entry is None:
        raise ValueError(f"Unknown citekey: {citekey}")

    record = _load_record(config, citekey)

    extracted_text = ""
    if record.extracted_path:
        extracted_file = Path(record.extracted_path)
        if extracted_file.exists():
            extracted_text = extracted_file.read_text(encoding="utf-8")
    ledger = load_budget_ledger(config.budget_ledger_file)
    record.processing_state = "local_processing"
    _save_record(config, record)

    outcome = generate_sections(
        config,
        entry,
        extracted_text,
        bibliography,
        current_daily_tokens=ledger.get("total_tokens", 0),
    )
    if outcome.status == "needs_approval":
        record.processing_state = "awaiting_fallback_approval"
        record.escalation_reason = outcome.escalation_reason
        record.fallback_provider = outcome.approval_request.fallback_provider if outcome.approval_request else ""
        record.fallback_model = outcome.approval_request.fallback_model if outcome.approval_request else ""
        record.approval_requested_at = utc_now_iso()
        record.local_attempts = outcome.local_attempts
        _save_record(config, record)
        resolver = approval_resolver or (lambda request: resolve_fallback_approval(config, request))
        decision = resolver(outcome.approval_request)
        record.approval_decision = decision
        if decision == "cancel":
            record.processing_state = "awaiting_fallback_approval"
            _save_record(config, record)
            raise RuntimeError("Queue cancelled during fallback approval.")
        if decision != "approve":
            record.processing_state = "needs_review"
            record.ingest_status = "needs_review"
            _save_record(config, record)
            raise ValueError("Fallback approval denied; source sent to review.")

        record.processing_state = "fallback_processing"
        _save_record(config, record)
        outcome = run_approved_fallback(
            config,
            entry,
            extracted_text,
            bibliography,
            outcome.approval_request,
            outcome.keyword_targets,
            outcome.keyword_links,
            outcome.keyword_tags,
        )
        if outcome.status != "success":
            record.processing_state = "needs_review"
            record.ingest_status = "needs_review"
            record.escalation_reason = outcome.escalation_reason
            record.provider = outcome.provider_name
            record.usage_summary = outcome.usage.as_dict() if outcome.usage else {}
            _save_record(config, record)
            raise ValueError(f"Fallback processing failed: {outcome.escalation_reason}")
        if config.show_completion_dialog and outcome.usage is not None:
            show_fallback_complete_dialog(citekey, entry.title, outcome.usage)
    elif outcome.status == "needs_review":
        record.processing_state = "needs_review"
        record.ingest_status = "needs_review"
        record.escalation_reason = outcome.escalation_reason
        record.local_attempts = outcome.local_attempts
        _save_record(config, record)
        show_info_dialog(f"Fallback blocked for {entry.title} [@{citekey}]\\n\\nReason: {outcome.escalation_reason}")
        raise ValueError(outcome.escalation_reason)

    assert outcome.sections is not None
    publish_error = _validate_publishable_note(config, entry, bibliography, extracted_text, outcome.sections)
    if publish_error:
        record.processing_state = "needs_review"
        record.ingest_status = "needs_review"
        record.escalation_reason = publish_error
        record.provider = outcome.provider_name
        record.local_attempts = max(record.local_attempts, outcome.local_attempts)
        record.usage_summary = outcome.usage.as_dict() if outcome.usage else {}
        _save_record(config, record)
        raise ValueError(publish_error)

    note_path = source_note_path(config.wiki_sources_dir, citekey)
    existing = note_path.read_text(encoding="utf-8") if note_path.exists() else None
    note_path.write_text(render_note(entry, record, outcome.sections, existing_note=existing), encoding="utf-8")

    record.provider = outcome.provider_name
    record.local_attempts = max(record.local_attempts, outcome.local_attempts)
    record.processing_state = "ingested"
    record.ingest_status = "ingested"
    record.usage_summary = outcome.usage.as_dict() if outcome.usage else {}
    _save_record(config, record)

    ensure_person_pages(config, entry)
    ensure_concept_pages(config, entry, outcome.sections)
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


def _persist_source_path(config: AppConfig, citekey: str, new_path: Path) -> None:
    registry = SourceRegistry.load(config.registry_file)
    record = registry.get(citekey)
    if record is None:
        return
    record.source_path = str(new_path)
    registry.upsert(record)
    registry.save()


def process_watch_folder(config: AppConfig) -> WatchSummary:
    ensure_runtime_directories(config)

    def _run() -> WatchSummary:
        summary = WatchSummary()
        sync_bibliography(config)
        items = iter_watch_items(config)

        for item in items:
            source_format = detect_source_format(item)
            summary.count_format(source_format)
            try:
                record, _match = register_source(config, item)
                if record.needs_review:
                    record.processing_state = "needs_review"
                    _save_record(config, record)
                    archive_watch_item(item, config.other_dir)
                    summary.issue_count += 1
                    continue

                record = extract_source(config, record.citekey)
                ingest_source(config, record.citekey)
                archived_path = archive_watch_item(item, config.processed_dir)
                _persist_source_path(config, record.citekey, archived_path)
                summary.success_count += 1
            except RuntimeError as exc:
                if "Queue cancelled" in str(exc):
                    summary.cancelled = True
                    break
                archive_watch_item(item, config.other_dir)
                summary.fail_count += 1
                failure_log = config.cache_dir / "watch_failures.log"
                with failure_log.open("a", encoding="utf-8") as handle:
                    handle.write(f"{item}\n{traceback.format_exc()}\n")
            except ValueError as exc:
                archive_watch_item(item, config.other_dir)
                if "approval denied" in str(exc).lower() or "needs_review" in str(exc).lower() or "cap" in str(exc).lower():
                    summary.issue_count += 1
                else:
                    summary.fail_count += 1
                failure_log = config.cache_dir / "watch_failures.log"
                with failure_log.open("a", encoding="utf-8") as handle:
                    handle.write(f"{item}\n{traceback.format_exc()}\n")
            except Exception:
                archive_watch_item(item, config.other_dir)
                summary.issue_count += 1
                failure_log = config.cache_dir / "watch_failures.log"
                with failure_log.open("a", encoding="utf-8") as handle:
                    handle.write(f"{item}\n{traceback.format_exc()}\n")

        return summary

    summary = timed_watch_run(_run)
    if config.show_completion_dialog:
        show_final_dialog(summary)
    return summary
