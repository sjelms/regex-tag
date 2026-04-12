from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PersonRecord:
    display_name: str
    wiki_link: str
    surname: str


@dataclass
class BibliographyEntry:
    citekey: str
    title: str
    entry_type: str
    year: str
    date: str
    abstract: str
    keywords: list[str]
    authors: list[PersonRecord] = field(default_factory=list)
    editors: list[PersonRecord] = field(default_factory=list)
    doi: str = ""
    isbn: str = ""
    url: str = ""
    publisher: str = ""
    journaltitle: str = ""
    institution: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "citekey": self.citekey,
            "title": self.title,
            "entry_type": self.entry_type,
            "year": self.year,
            "date": self.date,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "authors": [asdict(person) for person in self.authors],
            "editors": [asdict(person) for person in self.editors],
            "doi": self.doi,
            "isbn": self.isbn,
            "url": self.url,
            "publisher": self.publisher,
            "journaltitle": self.journaltitle,
            "institution": self.institution,
        }


@dataclass
class MatchResult:
    citekey: str = ""
    confidence: float = 0.0
    reason: str = ""
    needs_review: bool = True


@dataclass
class SourceRecord:
    citekey: str
    source_path: str
    source_format: str
    raw_hash: str
    match_reason: str
    confidence: float
    needs_review: bool
    extraction_status: str = "pending"
    ingest_status: str = "registered"
    extracted_path: str = ""
    provider: str = ""
    processing_state: str = "registered"
    escalation_reason: str = ""
    local_attempts: int = 0
    fallback_provider: str = ""
    fallback_model: str = ""
    approval_requested_at: str = ""
    approval_decision: str = ""
    usage_summary: dict[str, Any] = field(default_factory=dict)
    registered_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceRecord":
        return cls(**payload)


@dataclass
class WatchSummary:
    success_count: int = 0
    issue_count: int = 0
    fail_count: int = 0
    pdf_count: int = 0
    epub_count: int = 0
    markdown_count: int = 0
    other_count: int = 0
    elapsed_seconds: float = 0.0
    cancelled: bool = False

    def count_format(self, source_format: str) -> None:
        if source_format == "pdf":
            self.pdf_count += 1
        elif source_format in {"epub", "epub_package"}:
            self.epub_count += 1
        elif source_format in {"markdown", "xhtml"}:
            self.markdown_count += 1
        else:
            self.other_count += 1


@dataclass
class ProviderUsage:
    provider_name: str
    model: str
    requests_made: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_total_tokens: int
    estimated_cost: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApprovalRequest:
    citekey: str
    source_name: str
    reason: str
    primary_model: str
    fallback_provider: str
    fallback_model: str
    estimated_chunk_count: int
    usage: ProviderUsage
    current_daily_tokens: int
    max_daily_tokens: int


@dataclass
class GenerationOutcome:
    status: str
    sections: dict[str, Any] | None
    provider_name: str
    provider_model: str
    usage: ProviderUsage | None = None
    escalation_reason: str = ""
    approval_request: ApprovalRequest | None = None
    keyword_targets: list[str] = field(default_factory=list)
    keyword_tags: list[str] = field(default_factory=list)
    local_attempts: int = 0
