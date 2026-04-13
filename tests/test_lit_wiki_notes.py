import tempfile
import unittest
from pathlib import Path

from lit_wiki.models import BibliographyEntry, PersonRecord, SourceRecord
from lit_wiki.notes import render_note, source_note_path


class TestNoteRendering(unittest.TestCase):
    def test_renders_key_type_and_all_people(self):
        entry = BibliographyEntry(
            citekey="Alpha2024-ab",
            title="Example Book",
            entry_type="book",
            year="2024",
            date="2024-05-01",
            abstract="Abstract text.",
            keywords=["One", "Two"],
            authors=[
                PersonRecord("Alice Smith", "[[Alice Smith]]", "Smith"),
                PersonRecord("Bob Brown", "[[Bob Brown]]", "Brown"),
                PersonRecord("Carol Walker", "[[Carol Walker]]", "Walker"),
                PersonRecord("Dana Evans", "[[Dana Evans]]", "Evans"),
            ],
            editors=[PersonRecord("Emma Editor", "[[Emma Editor]]", "Editor")],
        )
        record = SourceRecord(
            citekey="Alpha2024-ab",
            source_path="/tmp/source.md",
            source_format="markdown",
            raw_hash="abc",
            match_reason="markdown citation-key",
            confidence=1.0,
            needs_review=False,
        )
        sections = {
            "summary_points": ["Point one."],
            "questions": ["Question one?"],
            "notes": ["Note one."],
            "abstract": "Abstract text.",
            "cross_reference_bibliography": ["- [[@Other2020-ab]] — Other"],
            "background": ["Context."],
            "methods": ["Methods."],
            "results": ["Results."],
            "data": ["Data."],
            "conclusions": ["Conclusion."],
            "next_steps": ["Next step."],
            "significance": ["Significance."],
            "related_references": ["Other2020-ab"],
        }
        note = render_note(entry, record, sections)
        self.assertIn('key: "[[@Alpha2024-ab]]"', note)
        self.assertIn('type: "[[@book]]"', note)
        self.assertIn('author - 4: "[[Dana Evans]]"', note)
        self.assertIn('editor - 1: "[[Emma Editor]]"', note)
        self.assertIn("- [[@Other2020-ab]]", note)

    def test_source_note_uses_wiki_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = source_note_path(Path(tmpdir), "Alpha2024-ab")
        self.assertEqual(path.name, "Alpha2024-ab_wiki.md")
