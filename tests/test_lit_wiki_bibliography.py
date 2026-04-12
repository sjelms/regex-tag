import tempfile
import textwrap
import unittest
from pathlib import Path

from lit_wiki.bibliography import parse_bibliography


class TestBibliographyParsing(unittest.TestCase):
    def test_parses_all_authors_editors_and_entry_type(self):
        bib_text = textwrap.dedent(
            """
            @BOOK{Alpha2024-ab,
              title = {Example Book},
              author = {Smith, Alice and Brown, Bob and Walker, Carol and Evans, Dana},
              editor = {Editor, Emma and Curator, Chris},
              date = {2024-05-01},
              abstract = {This is a test abstract.},
              keywords = {One;Two}
            }
            """
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            bib_path = Path(tmpdir) / "regex-tag.bib"
            bib_path.write_text(bib_text, encoding="utf-8")
            bibliography = parse_bibliography(bib_path)

        entry = bibliography.get("Alpha2024-ab")
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.entry_type, "book")
        self.assertEqual(entry.year, "2024")
        self.assertEqual([person.display_name for person in entry.authors], [
            "Alice Smith",
            "Bob Brown",
            "Carol Walker",
            "Dana Evans",
        ])
        self.assertEqual([person.display_name for person in entry.editors], [
            "Emma Editor",
            "Chris Curator",
        ])

