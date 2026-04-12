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
    registered_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceRecord":
        return cls(**payload)

