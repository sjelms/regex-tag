from __future__ import annotations

import json
from pathlib import Path

from pybtex.database.input import bibtex

from .models import BibliographyEntry, PersonRecord
from .utils import dedupe_casefold, first_year, normalize_text


def _person_record(person: "pybtex.database.Person") -> PersonRecord:
    first = " ".join(person.first_names + person.middle_names).strip()
    prelast = " ".join(person.prelast_names).strip()
    last = " ".join(person.last_names).strip()
    lineage = " ".join(person.lineage_names).strip()
    parts = [part for part in (first, prelast, last, lineage) if part]
    display_name = " ".join(parts).strip() or "Unknown Author"
    surname = last or display_name.split()[-1]
    return PersonRecord(
        display_name=display_name,
        wiki_link=f"[[{display_name}]]",
        surname=surname,
    )


class BibliographyIndex:
    def __init__(self, entries: dict[str, BibliographyEntry]) -> None:
        self.entries = entries
        self.title_index: dict[str, list[str]] = {}
        self.doi_index: dict[str, str] = {}
        for citekey, entry in entries.items():
            self.title_index.setdefault(normalize_text(entry.title), []).append(citekey)
            if entry.doi:
                self.doi_index[normalize_text(entry.doi)] = citekey

    def get(self, citekey: str) -> BibliographyEntry | None:
        return self.entries.get(citekey)

    def get_by_doi(self, doi: str) -> BibliographyEntry | None:
        if not doi:
            return None
        citekey = self.doi_index.get(normalize_text(doi))
        return self.entries.get(citekey) if citekey else None

    def find_by_title_authors_year(
        self,
        title: str,
        author_surnames: list[str],
        year: str,
    ) -> BibliographyEntry | None:
        title_key = normalize_text(title)
        candidates = [self.entries[citekey] for citekey in self.title_index.get(title_key, [])]
        if not candidates:
            return None

        normalized_surnames = {normalize_text(name) for name in author_surnames if name}
        for candidate in candidates:
            candidate_surnames = {
                normalize_text(person.surname)
                for person in (candidate.authors or candidate.editors)
                if person.surname
            }
            if year and candidate.year and year != candidate.year:
                continue
            if normalized_surnames and not normalized_surnames.issubset(candidate_surnames):
                continue
            return candidate

        for candidate in candidates:
            if year and candidate.year and year == candidate.year:
                return candidate
        return candidates[0]

    def same_author_entries(self, citekey: str, limit: int = 5) -> list[BibliographyEntry]:
        source = self.get(citekey)
        if source is None:
            return []
        target_surnames = {normalize_text(person.surname) for person in source.authors}
        related: list[BibliographyEntry] = []
        for candidate in self.entries.values():
            if candidate.citekey == citekey:
                continue
            candidate_surnames = {normalize_text(person.surname) for person in candidate.authors}
            if target_surnames and target_surnames & candidate_surnames:
                related.append(candidate)
        related.sort(key=lambda entry: (entry.year, entry.title))
        return related[:limit]


def parse_bibliography(path: Path) -> BibliographyIndex:
    parser = bibtex.Parser()
    database = parser.parse_file(str(path))
    entries: dict[str, BibliographyEntry] = {}

    for citekey, entry in database.entries.items():
        fields = entry.fields
        authors = [_person_record(person) for person in entry.persons.get("author", [])]
        editors = [_person_record(person) for person in entry.persons.get("editor", [])]
        raw_keywords = fields.get("keywords", "")
        keywords = dedupe_casefold([part.strip() for part in raw_keywords.split(";") if part.strip()])
        bib_entry = BibliographyEntry(
            citekey=citekey,
            title=fields.get("title", citekey).replace("\n", " ").strip(),
            entry_type=entry.type,
            year=first_year(fields.get("date") or fields.get("year")),
            date=fields.get("date") or fields.get("year", ""),
            abstract=fields.get("abstract", "").strip(),
            keywords=keywords,
            authors=authors,
            editors=editors,
            doi=fields.get("doi", ""),
            isbn=fields.get("isbn", ""),
            url=fields.get("url", ""),
            publisher=fields.get("publisher", ""),
            journaltitle=fields.get("journaltitle", ""),
            institution=fields.get("institution", ""),
        )
        entries[citekey] = bib_entry

    return BibliographyIndex(entries)


def write_registry(index: BibliographyIndex, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {citekey: entry.as_dict() for citekey, entry in index.entries.items()}
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
